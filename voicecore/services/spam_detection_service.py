"""
Spam detection service for VoiceCore AI.

Provides comprehensive spam call detection with configurable rules,
machine learning-based scoring, and real-time analysis for the
multitenant virtual receptionist system.
"""

import re
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import SpamRule, SpamReport, Call, CallType
from voicecore.logging import get_logger
from voicecore.config import settings


logger = get_logger(__name__)


class SpamDetectionError(Exception):
    """Base exception for spam detection errors."""
    pass


class SpamRuleNotFoundError(SpamDetectionError):
    """Raised when a spam rule is not found."""
    pass


class InvalidSpamRuleError(SpamDetectionError):
    """Raised when a spam rule is invalid."""
    pass


class SpamScore:
    """Represents a spam detection score and analysis."""
    
    def __init__(
        self,
        score: float,
        reasons: List[str],
        action: str,
        triggered_rules: List[uuid.UUID],
        confidence: float = 1.0
    ):
        self.score = score  # 0-1, higher = more likely spam
        self.reasons = reasons
        self.action = action  # 'allow', 'block', 'challenge', 'flag'
        self.triggered_rules = triggered_rules
        self.confidence = confidence
    
    @property
    def is_spam(self) -> bool:
        """Check if score indicates spam."""
        return self.score >= settings.spam_detection_threshold
    
    @property
    def should_block(self) -> bool:
        """Check if call should be blocked."""
        return self.action == 'block'
    
    @property
    def should_challenge(self) -> bool:
        """Check if call should be challenged."""
        return self.action == 'challenge'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "score": self.score,
            "reasons": self.reasons,
            "action": self.action,
            "triggered_rules": [str(rule_id) for rule_id in self.triggered_rules],
            "confidence": self.confidence,
            "is_spam": self.is_spam,
            "should_block": self.should_block,
            "should_challenge": self.should_challenge
        }


class SpamDetectionService:
    """
    Comprehensive spam detection service.
    
    Analyzes incoming calls using configurable rules, pattern matching,
    and behavioral analysis to identify and handle spam calls.
    """
    
    def __init__(self):
        self.logger = logger
        self._rule_cache = {}  # Cache for frequently used rules
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    async def analyze_call(
        self,
        tenant_id: uuid.UUID,
        phone_number: str,
        call_context: Optional[Dict[str, Any]] = None
    ) -> SpamScore:
        """
        Analyze a call for spam indicators.
        
        Args:
            tenant_id: Tenant UUID
            phone_number: Caller's phone number
            call_context: Additional context about the call
            
        Returns:
            SpamScore: Spam analysis results
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get active spam rules for tenant
                rules = await self._get_active_rules(session, tenant_id)
                
                # Initialize scoring
                total_score = 0.0
                triggered_rules = []
                reasons = []
                max_action_priority = 0
                final_action = "allow"
                
                # Action priority mapping
                action_priorities = {
                    "allow": 0,
                    "flag": 1,
                    "challenge": 2,
                    "block": 3
                }
                
                # Analyze against each rule
                for rule in rules:
                    match_result = await self._evaluate_rule(
                        rule, phone_number, call_context
                    )
                    
                    if match_result["matches"]:
                        # Calculate weighted score contribution
                        rule_contribution = (rule.weight / 100.0) * rule.confidence_score
                        total_score += rule_contribution
                        
                        triggered_rules.append(rule.id)
                        reasons.append(f"{rule.name}: {match_result['reason']}")
                        
                        # Update rule statistics
                        await self._update_rule_stats(session, rule.id)
                        
                        # Determine highest priority action
                        rule_action_priority = action_priorities.get(rule.action, 0)
                        if rule_action_priority > max_action_priority:
                            max_action_priority = rule_action_priority
                            final_action = rule.action
                
                # Normalize score to 0-1 range
                normalized_score = min(1.0, total_score)
                
                # Apply additional behavioral analysis
                behavioral_score = await self._analyze_behavior(
                    session, tenant_id, phone_number, call_context
                )
                
                # Combine scores (weighted average)
                final_score = (normalized_score * 0.7) + (behavioral_score * 0.3)
                final_score = min(1.0, final_score)
                
                # Override action based on final score if needed
                if final_score >= 0.9 and final_action != "block":
                    final_action = "block"
                    reasons.append("High composite spam score")
                elif final_score >= 0.7 and final_action == "allow":
                    final_action = "challenge"
                    reasons.append("Moderate spam indicators")
                
                spam_score = SpamScore(
                    score=final_score,
                    reasons=reasons,
                    action=final_action,
                    triggered_rules=triggered_rules,
                    confidence=min(1.0, len(triggered_rules) * 0.2 + 0.5)
                )
                
                self.logger.info(
                    "Spam analysis completed",
                    tenant_id=str(tenant_id),
                    phone_number=phone_number,
                    spam_score=final_score,
                    action=final_action,
                    triggered_rules=len(triggered_rules)
                )
                
                return spam_score
                
        except Exception as e:
            self.logger.error(
                "Spam analysis failed",
                tenant_id=str(tenant_id),
                phone_number=phone_number,
                error=str(e)
            )
            # Return safe default on error
            return SpamScore(
                score=0.0,
                reasons=["Analysis error"],
                action="allow",
                triggered_rules=[],
                confidence=0.0
            )
    
    async def create_spam_rule(
        self,
        tenant_id: uuid.UUID,
        rule_data: Dict[str, Any]
    ) -> SpamRule:
        """
        Create a new spam detection rule.
        
        Args:
            tenant_id: Tenant UUID
            rule_data: Rule configuration data
            
        Returns:
            SpamRule: Created spam rule
            
        Raises:
            InvalidSpamRuleError: If rule data is invalid
        """
        try:
            # Validate rule data
            self._validate_rule_data(rule_data)
            
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                rule = SpamRule(
                    tenant_id=tenant_id,
                    name=rule_data["name"],
                    description=rule_data.get("description"),
                    rule_type=rule_data["rule_type"],
                    pattern=rule_data["pattern"],
                    is_regex=rule_data.get("is_regex", False),
                    case_sensitive=rule_data.get("case_sensitive", False),
                    weight=rule_data.get("weight", 10),
                    threshold=rule_data.get("threshold", 0.8),
                    action=rule_data.get("action", "flag"),
                    response_message=rule_data.get("response_message"),
                    apply_to_numbers=rule_data.get("apply_to_numbers", []),
                    exclude_numbers=rule_data.get("exclude_numbers", []),
                    time_conditions=rule_data.get("time_conditions", {}),
                    is_active=rule_data.get("is_active", True),
                    is_global=rule_data.get("is_global", False),
                    auto_learn=rule_data.get("auto_learn", False),
                    source=rule_data.get("source", "manual"),
                    created_by=rule_data.get("created_by"),
                    metadata=rule_data.get("metadata", {})
                )
                
                session.add(rule)
                await session.commit()
                
                # Clear rule cache
                self._clear_rule_cache(tenant_id)
                
                self.logger.info(
                    "Spam rule created",
                    tenant_id=str(tenant_id),
                    rule_id=str(rule.id),
                    rule_name=rule.name,
                    rule_type=rule.rule_type
                )
                
                return rule
                
        except Exception as e:
            self.logger.error("Failed to create spam rule", error=str(e))
            raise SpamDetectionError(f"Failed to create spam rule: {str(e)}")
    
    async def update_spam_rule(
        self,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID,
        update_data: Dict[str, Any]
    ) -> Optional[SpamRule]:
        """
        Update an existing spam rule.
        
        Args:
            tenant_id: Tenant UUID
            rule_id: Rule UUID
            update_data: Fields to update
            
        Returns:
            Optional[SpamRule]: Updated rule or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(SpamRule).where(
                        and_(
                            SpamRule.id == rule_id,
                            SpamRule.tenant_id == tenant_id
                        )
                    )
                )
                rule = result.scalar_one_or_none()
                
                if not rule:
                    raise SpamRuleNotFoundError(f"Spam rule {rule_id} not found")
                
                # Update allowed fields
                allowed_fields = [
                    'name', 'description', 'pattern', 'is_regex', 'case_sensitive',
                    'weight', 'threshold', 'action', 'response_message',
                    'apply_to_numbers', 'exclude_numbers', 'time_conditions',
                    'is_active', 'auto_learn', 'metadata'
                ]
                
                for field, value in update_data.items():
                    if field in allowed_fields and hasattr(rule, field):
                        setattr(rule, field, value)
                
                rule.updated_at = datetime.utcnow()
                await session.commit()
                
                # Clear rule cache
                self._clear_rule_cache(tenant_id)
                
                self.logger.info(
                    "Spam rule updated",
                    tenant_id=str(tenant_id),
                    rule_id=str(rule_id),
                    updated_fields=list(update_data.keys())
                )
                
                return rule
                
        except SpamRuleNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Failed to update spam rule", rule_id=str(rule_id), error=str(e))
            raise SpamDetectionError(f"Failed to update spam rule: {str(e)}")
    
    async def delete_spam_rule(
        self,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID
    ) -> bool:
        """
        Delete a spam rule.
        
        Args:
            tenant_id: Tenant UUID
            rule_id: Rule UUID
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(SpamRule).where(
                        and_(
                            SpamRule.id == rule_id,
                            SpamRule.tenant_id == tenant_id
                        )
                    )
                )
                rule = result.scalar_one_or_none()
                
                if not rule:
                    raise SpamRuleNotFoundError(f"Spam rule {rule_id} not found")
                
                # Soft delete - mark as inactive
                rule.is_active = False
                rule.updated_at = datetime.utcnow()
                
                await session.commit()
                
                # Clear rule cache
                self._clear_rule_cache(tenant_id)
                
                self.logger.info(
                    "Spam rule deleted",
                    tenant_id=str(tenant_id),
                    rule_id=str(rule_id)
                )
                
                return True
                
        except SpamRuleNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Failed to delete spam rule", rule_id=str(rule_id), error=str(e))
            return False
    
    async def list_spam_rules(
        self,
        tenant_id: uuid.UUID,
        rule_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SpamRule]:
        """
        List spam rules with filtering.
        
        Args:
            tenant_id: Tenant UUID
            rule_type: Filter by rule type
            is_active: Filter by active status
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List[SpamRule]: List of spam rules
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                query = select(SpamRule)
                conditions = [SpamRule.tenant_id == tenant_id]
                
                if rule_type:
                    conditions.append(SpamRule.rule_type == rule_type)
                
                if is_active is not None:
                    conditions.append(SpamRule.is_active == is_active)
                
                query = query.where(and_(*conditions))
                query = query.offset(skip).limit(limit).order_by(SpamRule.name)
                
                result = await session.execute(query)
                rules = result.scalars().all()
                
                return list(rules)
                
        except Exception as e:
            self.logger.error("Failed to list spam rules", error=str(e))
            return []
    
    async def report_spam(
        self,
        tenant_id: uuid.UUID,
        phone_number: str,
        is_spam: bool,
        call_id: Optional[uuid.UUID] = None,
        reported_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> SpamReport:
        """
        Report spam feedback for learning and improvement.
        
        Args:
            tenant_id: Tenant UUID
            phone_number: Phone number to report
            is_spam: Whether this is confirmed spam
            call_id: Associated call ID
            reported_by: Who reported this
            notes: Additional notes
            
        Returns:
            SpamReport: Created spam report
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get current spam score for this number
                current_score = await self.analyze_call(tenant_id, phone_number)
                
                report = SpamReport(
                    tenant_id=tenant_id,
                    call_id=call_id,
                    phone_number=phone_number,
                    spam_score=current_score.score,
                    triggered_rules=[str(rule_id) for rule_id in current_score.triggered_rules],
                    detection_method="manual_report",
                    action_taken="reported",
                    is_confirmed_spam=is_spam,
                    feedback_notes=notes,
                    reported_by=reported_by,
                    metadata=current_score.to_dict()
                )
                
                session.add(report)
                await session.commit()
                
                # Update rule confidence based on feedback
                await self._process_feedback(session, current_score.triggered_rules, is_spam)
                
                self.logger.info(
                    "Spam report created",
                    tenant_id=str(tenant_id),
                    phone_number=phone_number,
                    is_spam=is_spam,
                    reported_by=reported_by
                )
                
                return report
                
        except Exception as e:
            self.logger.error("Failed to create spam report", error=str(e))
            raise SpamDetectionError(f"Failed to create spam report: {str(e)}")
    
    async def get_spam_statistics(
        self,
        tenant_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get spam detection statistics.
        
        Args:
            tenant_id: Tenant UUID
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dict[str, Any]: Spam statistics
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                if not end_date:
                    end_date = datetime.utcnow()
                if not start_date:
                    start_date = end_date - timedelta(days=30)
                
                # Get spam call statistics
                spam_calls_result = await session.execute(
                    select(
                        func.count(Call.id).label('total_calls'),
                        func.count(
                            func.case([(Call.call_type == CallType.SPAM, 1)])
                        ).label('spam_calls'),
                        func.avg(Call.spam_score).label('avg_spam_score')
                    )
                    .where(
                        and_(
                            Call.tenant_id == tenant_id,
                            Call.created_at >= start_date,
                            Call.created_at <= end_date
                        )
                    )
                )
                call_stats = spam_calls_result.fetchone()
                
                # Get rule effectiveness
                rule_stats_result = await session.execute(
                    select(
                        func.count(SpamRule.id).label('total_rules'),
                        func.count(
                            func.case([(SpamRule.is_active == True, 1)])
                        ).label('active_rules'),
                        func.avg(SpamRule.confidence_score).label('avg_confidence'),
                        func.sum(SpamRule.match_count).label('total_matches')
                    )
                    .where(SpamRule.tenant_id == tenant_id)
                )
                rule_stats = rule_stats_result.fetchone()
                
                # Get recent reports
                recent_reports_result = await session.execute(
                    select(
                        func.count(SpamReport.id).label('total_reports'),
                        func.count(
                            func.case([(SpamReport.is_confirmed_spam == True, 1)])
                        ).label('confirmed_spam'),
                        func.count(
                            func.case([(SpamReport.is_confirmed_spam == False, 1)])
                        ).label('false_positives')
                    )
                    .where(
                        and_(
                            SpamReport.tenant_id == tenant_id,
                            SpamReport.created_at >= start_date,
                            SpamReport.created_at <= end_date
                        )
                    )
                )
                report_stats = recent_reports_result.fetchone()
                
                return {
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "calls": {
                        "total": call_stats[0] or 0,
                        "spam_detected": call_stats[1] or 0,
                        "spam_rate": (call_stats[1] / call_stats[0]) if call_stats[0] else 0,
                        "average_spam_score": float(call_stats[2] or 0)
                    },
                    "rules": {
                        "total": rule_stats[0] or 0,
                        "active": rule_stats[1] or 0,
                        "average_confidence": float(rule_stats[2] or 0),
                        "total_matches": rule_stats[3] or 0
                    },
                    "reports": {
                        "total": report_stats[0] or 0,
                        "confirmed_spam": report_stats[1] or 0,
                        "false_positives": report_stats[2] or 0,
                        "accuracy_rate": (
                            (report_stats[1] / report_stats[0]) 
                            if report_stats[0] else 1.0
                        )
                    }
                }
                
        except Exception as e:
            self.logger.error("Failed to get spam statistics", error=str(e))
            return {}
    
    # Private helper methods
    
    async def _get_active_rules(
        self,
        session,
        tenant_id: uuid.UUID
    ) -> List[SpamRule]:
        """Get active spam rules for tenant."""
        cache_key = f"rules_{tenant_id}"
        
        # Check cache first
        if cache_key in self._rule_cache:
            cache_entry = self._rule_cache[cache_key]
            if datetime.utcnow() - cache_entry["timestamp"] < timedelta(seconds=self._cache_ttl):
                return cache_entry["rules"]
        
        # Fetch from database
        result = await session.execute(
            select(SpamRule)
            .where(
                and_(
                    SpamRule.tenant_id == tenant_id,
                    SpamRule.is_active == True
                )
            )
            .order_by(desc(SpamRule.weight))
        )
        rules = result.scalars().all()
        
        # Cache the results
        self._rule_cache[cache_key] = {
            "rules": list(rules),
            "timestamp": datetime.utcnow()
        }
        
        return list(rules)
    
    async def _evaluate_rule(
        self,
        rule: SpamRule,
        phone_number: str,
        call_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate a single spam rule against call data."""
        try:
            # Check number inclusion/exclusion
            if rule.apply_to_numbers:
                if not self._matches_number_patterns(phone_number, rule.apply_to_numbers):
                    return {"matches": False, "reason": "Number not in apply list"}
            
            if rule.exclude_numbers:
                if self._matches_number_patterns(phone_number, rule.exclude_numbers):
                    return {"matches": False, "reason": "Number in exclude list"}
            
            # Check time conditions
            if rule.time_conditions and not self._matches_time_conditions(rule.time_conditions):
                return {"matches": False, "reason": "Time conditions not met"}
            
            # Evaluate pattern based on rule type
            if rule.rule_type == "keyword":
                return self._evaluate_keyword_rule(rule, call_context)
            elif rule.rule_type == "pattern":
                return self._evaluate_pattern_rule(rule, phone_number, call_context)
            elif rule.rule_type == "number":
                return self._evaluate_number_rule(rule, phone_number)
            elif rule.rule_type == "behavior":
                return self._evaluate_behavior_rule(rule, call_context)
            else:
                return {"matches": False, "reason": "Unknown rule type"}
                
        except Exception as e:
            self.logger.warning(f"Rule evaluation error: {e}")
            return {"matches": False, "reason": "Evaluation error"}
    
    def _evaluate_keyword_rule(
        self,
        rule: SpamRule,
        call_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate keyword-based spam rule."""
        if not call_context or "transcript" not in call_context:
            return {"matches": False, "reason": "No transcript available"}
        
        transcript = call_context["transcript"]
        pattern = rule.pattern
        
        if not rule.case_sensitive:
            transcript = transcript.lower()
            pattern = pattern.lower()
        
        if rule.is_regex:
            try:
                if re.search(pattern, transcript):
                    return {"matches": True, "reason": f"Regex pattern '{rule.pattern}' found in transcript"}
            except re.error:
                return {"matches": False, "reason": "Invalid regex pattern"}
        else:
            if pattern in transcript:
                return {"matches": True, "reason": f"Keyword '{rule.pattern}' found in transcript"}
        
        return {"matches": False, "reason": "Pattern not found"}
    
    def _evaluate_pattern_rule(
        self,
        rule: SpamRule,
        phone_number: str,
        call_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate pattern-based spam rule."""
        text_to_check = phone_number
        
        if call_context and "transcript" in call_context:
            text_to_check += " " + call_context["transcript"]
        
        pattern = rule.pattern
        
        if not rule.case_sensitive:
            text_to_check = text_to_check.lower()
            pattern = pattern.lower()
        
        if rule.is_regex:
            try:
                if re.search(pattern, text_to_check):
                    return {"matches": True, "reason": f"Pattern '{rule.pattern}' matched"}
            except re.error:
                return {"matches": False, "reason": "Invalid regex pattern"}
        else:
            if pattern in text_to_check:
                return {"matches": True, "reason": f"Pattern '{rule.pattern}' found"}
        
        return {"matches": False, "reason": "Pattern not found"}
    
    def _evaluate_number_rule(
        self,
        rule: SpamRule,
        phone_number: str
    ) -> Dict[str, Any]:
        """Evaluate number-based spam rule."""
        pattern = rule.pattern
        
        if rule.is_regex:
            try:
                if re.match(pattern, phone_number):
                    return {"matches": True, "reason": f"Phone number matches pattern '{pattern}'"}
            except re.error:
                return {"matches": False, "reason": "Invalid regex pattern"}
        else:
            if pattern in phone_number:
                return {"matches": True, "reason": f"Phone number contains '{pattern}'"}
        
        return {"matches": False, "reason": "Number pattern not matched"}
    
    def _evaluate_behavior_rule(
        self,
        rule: SpamRule,
        call_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate behavior-based spam rule."""
        if not call_context:
            return {"matches": False, "reason": "No call context available"}
        
        # This would implement behavioral analysis
        # For now, return a simple implementation
        return {"matches": False, "reason": "Behavior analysis not implemented"}
    
    def _matches_number_patterns(
        self,
        phone_number: str,
        patterns: List[str]
    ) -> bool:
        """Check if phone number matches any of the given patterns."""
        for pattern in patterns:
            try:
                if re.match(pattern, phone_number):
                    return True
            except re.error:
                # If regex is invalid, try simple string matching
                if pattern in phone_number:
                    return True
        return False
    
    def _matches_time_conditions(
        self,
        time_conditions: Dict[str, Any]
    ) -> bool:
        """Check if current time matches the time conditions."""
        now = datetime.utcnow()
        
        # Simple implementation - can be extended
        if "hours" in time_conditions:
            current_hour = now.hour
            allowed_hours = time_conditions["hours"]
            if isinstance(allowed_hours, list):
                return current_hour in allowed_hours
        
        return True  # Default to allowing if no specific conditions
    
    async def _analyze_behavior(
        self,
        session,
        tenant_id: uuid.UUID,
        phone_number: str,
        call_context: Optional[Dict[str, Any]]
    ) -> float:
        """Analyze caller behavior for spam indicators."""
        try:
            # Get call history for this number
            call_history_result = await session.execute(
                select(
                    func.count(Call.id).label('call_count'),
                    func.avg(Call.duration).label('avg_duration'),
                    func.max(Call.created_at).label('last_call')
                )
                .where(
                    and_(
                        Call.tenant_id == tenant_id,
                        Call.from_number == phone_number,
                        Call.created_at >= datetime.utcnow() - timedelta(days=30)
                    )
                )
            )
            history = call_history_result.fetchone()
            
            behavior_score = 0.0
            
            # Frequent calls in short time = suspicious
            if history[0] and history[0] > 10:  # More than 10 calls in 30 days
                behavior_score += 0.3
            
            # Very short calls = suspicious
            if history[1] and history[1] < 10:  # Average duration less than 10 seconds
                behavior_score += 0.2
            
            # Recent repeated calls = suspicious
            if history[2] and (datetime.utcnow() - history[2]).total_seconds() < 3600:
                behavior_score += 0.2
            
            return min(1.0, behavior_score)
            
        except Exception as e:
            self.logger.warning(f"Behavior analysis error: {e}")
            return 0.0
    
    async def _update_rule_stats(self, session, rule_id: uuid.UUID):
        """Update rule match statistics."""
        try:
            await session.execute(
                update(SpamRule)
                .where(SpamRule.id == rule_id)
                .values(
                    match_count=SpamRule.match_count + 1,
                    last_matched_at=datetime.utcnow()
                )
            )
        except Exception as e:
            self.logger.warning(f"Failed to update rule stats: {e}")
    
    async def _process_feedback(
        self,
        session,
        triggered_rules: List[uuid.UUID],
        is_spam: bool
    ):
        """Process user feedback to improve rule confidence."""
        try:
            for rule_id in triggered_rules:
                if is_spam:
                    # Positive feedback - increase confidence
                    await session.execute(
                        update(SpamRule)
                        .where(SpamRule.id == rule_id)
                        .values(
                            confidence_score=func.least(1.0, SpamRule.confidence_score + 0.01)
                        )
                    )
                else:
                    # False positive - decrease confidence and increment counter
                    await session.execute(
                        update(SpamRule)
                        .where(SpamRule.id == rule_id)
                        .values(
                            confidence_score=func.greatest(0.1, SpamRule.confidence_score - 0.05),
                            false_positive_count=SpamRule.false_positive_count + 1
                        )
                    )
        except Exception as e:
            self.logger.warning(f"Failed to process feedback: {e}")
    
    def _validate_rule_data(self, rule_data: Dict[str, Any]):
        """Validate spam rule data."""
        required_fields = ["name", "rule_type", "pattern"]
        
        for field in required_fields:
            if field not in rule_data:
                raise InvalidSpamRuleError(f"Missing required field: {field}")
        
        valid_rule_types = ["keyword", "pattern", "number", "behavior"]
        if rule_data["rule_type"] not in valid_rule_types:
            raise InvalidSpamRuleError(f"Invalid rule type: {rule_data['rule_type']}")
        
        valid_actions = ["allow", "flag", "challenge", "block"]
        if "action" in rule_data and rule_data["action"] not in valid_actions:
            raise InvalidSpamRuleError(f"Invalid action: {rule_data['action']}")
        
        if "weight" in rule_data:
            weight = rule_data["weight"]
            if not isinstance(weight, int) or weight < 1 or weight > 100:
                raise InvalidSpamRuleError("Weight must be an integer between 1 and 100")
    
    def _clear_rule_cache(self, tenant_id: uuid.UUID):
        """Clear rule cache for tenant."""
        cache_key = f"rules_{tenant_id}"
        if cache_key in self._rule_cache:
            del self._rule_cache[cache_key]