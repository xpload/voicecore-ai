"""
AI Training Service for VoiceCore AI.

Implements training mode, custom response scripts, and A/B testing
per Requirements 12.1, 12.2, and 12.4.
"""

import uuid
import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy import select, and_, func, desc, update
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import KnowledgeBase, Call, Agent, Tenant
from voicecore.services.openai_service import OpenAIService
from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class TrainingMode(Enum):
    """AI training modes."""
    PRODUCTION = "production"
    TRAINING = "training"
    A_B_TEST = "a_b_test"
    SIMULATION = "simulation"


class ResponseStrategy(Enum):
    """Response strategy types."""
    DEFAULT = "default"
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    EMPATHETIC = "empathetic"


class TestStatus(Enum):
    """A/B test status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class CustomResponseScript:
    """Custom response script configuration."""
    id: str
    name: str
    description: str
    tenant_id: uuid.UUID
    trigger_keywords: List[str]
    response_template: str
    variables: Dict[str, Any]
    strategy: ResponseStrategy
    enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime


@dataclass
class ABTestConfiguration:
    """A/B test configuration."""
    id: str
    name: str
    description: str
    tenant_id: uuid.UUID
    status: TestStatus
    strategy_a: ResponseStrategy
    strategy_b: ResponseStrategy
    traffic_split: float  # 0.0 to 1.0 (percentage for strategy A)
    success_metric: str  # "transfer_rate", "satisfaction", "resolution_time"
    target_sample_size: int
    start_date: datetime
    end_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass
class ABTestResult:
    """A/B test result data."""
    test_id: str
    strategy: ResponseStrategy
    sample_size: int
    success_rate: float
    average_response_time: float
    transfer_rate: float
    satisfaction_score: Optional[float]
    confidence_interval: Tuple[float, float]
    statistical_significance: bool


@dataclass
class TrainingSession:
    """AI training session data."""
    id: str
    tenant_id: uuid.UUID
    mode: TrainingMode
    script_id: Optional[str]
    test_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    total_interactions: int
    successful_interactions: int
    feedback_scores: List[float]
    improvements_identified: List[str]


class AITrainingService:
    """
    Comprehensive AI training and optimization service.
    
    Implements training mode, custom response scripts, and A/B testing
    per Requirements 12.1, 12.2, and 12.4.
    """
    
    def __init__(self):
        self.logger = logger
        self.openai_service = OpenAIService()
        
        # Training state management
        self.active_training_sessions: Dict[str, TrainingSession] = {}
        self.custom_scripts: Dict[str, CustomResponseScript] = {}
        self.ab_tests: Dict[str, ABTestConfiguration] = {}
        
        # Response templates
        self.response_templates = {
            ResponseStrategy.DEFAULT: {
                "greeting": "Hello! Thank you for calling {company_name}. How can I help you today?",
                "transfer": "I'll connect you with {department} right away. Please hold for a moment.",
                "unavailable": "I'm sorry, but {department} is currently unavailable. Would you like to leave a voicemail or try again later?",
                "closing": "Thank you for calling {company_name}. Have a great day!"
            },
            ResponseStrategy.FORMAL: {
                "greeting": "Good {time_of_day}. You have reached {company_name}. How may I assist you today?",
                "transfer": "Certainly. I will transfer your call to {department} immediately. Please remain on the line.",
                "unavailable": "I regret to inform you that {department} is presently unavailable. May I take a message or would you prefer to call back?",
                "closing": "Thank you for contacting {company_name}. We appreciate your business."
            },
            ResponseStrategy.CASUAL: {
                "greeting": "Hi there! Thanks for calling {company_name}. What can I do for you?",
                "transfer": "Sure thing! Let me get you over to {department}. Just a sec!",
                "unavailable": "Oh no, looks like {department} is busy right now. Want to leave a message or call back later?",
                "closing": "Thanks for calling {company_name}! Take care!"
            },
            ResponseStrategy.TECHNICAL: {
                "greeting": "Welcome to {company_name} technical support. Please describe your technical issue.",
                "transfer": "Routing your call to {department} technical specialist. Transferring now.",
                "unavailable": "{department} technical team is at capacity. Current wait time is {wait_time} minutes. Continue holding or request callback?",
                "closing": "Your technical inquiry has been processed. Reference number: {ticket_id}. Thank you."
            },
            ResponseStrategy.EMPATHETIC: {
                "greeting": "Hello, and thank you for reaching out to {company_name}. I understand you may need assistance, and I'm here to help.",
                "transfer": "I completely understand your needs. Let me connect you with {department} who can provide the best support for your situation.",
                "unavailable": "I know this might be frustrating, but {department} is helping other customers right now. I'd be happy to take your information so they can call you back.",
                "closing": "I hope we were able to help you today. Thank you for choosing {company_name}, and please don't hesitate to call if you need anything else."
            }
        }
    
    async def create_custom_response_script(
        self,
        tenant_id: uuid.UUID,
        name: str,
        description: str,
        trigger_keywords: List[str],
        response_template: str,
        variables: Dict[str, Any],
        strategy: ResponseStrategy = ResponseStrategy.DEFAULT,
        priority: int = 1
    ) -> CustomResponseScript:
        """
        Create a custom response script for AI training.
        
        Args:
            tenant_id: Tenant ID
            name: Script name
            description: Script description
            trigger_keywords: Keywords that trigger this script
            response_template: Template with variables
            variables: Variable definitions
            strategy: Response strategy type
            priority: Script priority (higher = more priority)
            
        Returns:
            CustomResponseScript object
        """
        try:
            script_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            script = CustomResponseScript(
                id=script_id,
                name=name,
                description=description,
                tenant_id=tenant_id,
                trigger_keywords=trigger_keywords,
                response_template=response_template,
                variables=variables,
                strategy=strategy,
                enabled=True,
                priority=priority,
                created_at=current_time,
                updated_at=current_time
            )
            
            # Store in memory (in production, store in database)
            self.custom_scripts[script_id] = script
            
            # Store in database
            await self._store_script_in_database(script)
            
            self.logger.info(
                "Custom response script created",
                script_id=script_id,
                tenant_id=str(tenant_id),
                name=name,
                strategy=strategy.value
            )
            
            return script
            
        except Exception as e:
            self.logger.error("Failed to create custom response script", error=str(e))
            raise
    
    async def update_response_script(
        self,
        script_id: str,
        tenant_id: uuid.UUID,
        **updates
    ) -> Optional[CustomResponseScript]:
        """
        Update an existing response script.
        
        Args:
            script_id: Script ID to update
            tenant_id: Tenant ID for security
            **updates: Fields to update
            
        Returns:
            Updated CustomResponseScript or None
        """
        try:
            if script_id not in self.custom_scripts:
                return None
            
            script = self.custom_scripts[script_id]
            
            # Verify tenant ownership
            if script.tenant_id != tenant_id:
                return None
            
            # Update fields
            for field, value in updates.items():
                if hasattr(script, field):
                    setattr(script, field, value)
            
            script.updated_at = datetime.utcnow()
            
            # Update in database
            await self._update_script_in_database(script)
            
            self.logger.info(
                "Response script updated",
                script_id=script_id,
                tenant_id=str(tenant_id),
                updates=list(updates.keys())
            )
            
            return script
            
        except Exception as e:
            self.logger.error("Failed to update response script", error=str(e))
            return None
    
    async def start_training_mode(
        self,
        tenant_id: uuid.UUID,
        mode: TrainingMode = TrainingMode.TRAINING,
        script_id: Optional[str] = None,
        test_id: Optional[str] = None
    ) -> TrainingSession:
        """
        Start an AI training session.
        
        Args:
            tenant_id: Tenant ID
            mode: Training mode
            script_id: Optional script ID for testing
            test_id: Optional A/B test ID
            
        Returns:
            TrainingSession object
        """
        try:
            session_id = str(uuid.uuid4())
            
            session = TrainingSession(
                id=session_id,
                tenant_id=tenant_id,
                mode=mode,
                script_id=script_id,
                test_id=test_id,
                start_time=datetime.utcnow(),
                end_time=None,
                total_interactions=0,
                successful_interactions=0,
                feedback_scores=[],
                improvements_identified=[]
            )
            
            self.active_training_sessions[session_id] = session
            
            self.logger.info(
                "Training session started",
                session_id=session_id,
                tenant_id=str(tenant_id),
                mode=mode.value,
                script_id=script_id,
                test_id=test_id
            )
            
            return session
            
        except Exception as e:
            self.logger.error("Failed to start training session", error=str(e))
            raise
    
    async def process_training_interaction(
        self,
        session_id: str,
        user_input: str,
        ai_response: str,
        success: bool,
        feedback_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a training interaction and collect feedback.
        
        Args:
            session_id: Training session ID
            user_input: User's input
            ai_response: AI's response
            success: Whether interaction was successful
            feedback_score: Optional feedback score (1-5)
            metadata: Optional metadata
            
        Returns:
            Dict containing interaction analysis
        """
        try:
            if session_id not in self.active_training_sessions:
                raise ValueError(f"Training session {session_id} not found")
            
            session = self.active_training_sessions[session_id]
            session.total_interactions += 1
            
            if success:
                session.successful_interactions += 1
            
            if feedback_score is not None:
                session.feedback_scores.append(feedback_score)
            
            # Analyze interaction for improvements
            analysis = await self._analyze_training_interaction(
                user_input, ai_response, success, feedback_score, metadata
            )
            
            # Add improvements to session
            if analysis.get("improvements"):
                session.improvements_identified.extend(analysis["improvements"])
            
            # Generate response using current training configuration
            if session.script_id:
                enhanced_response = await self._generate_enhanced_response(
                    session.script_id, user_input, session.tenant_id
                )
                analysis["enhanced_response"] = enhanced_response
            
            self.logger.info(
                "Training interaction processed",
                session_id=session_id,
                success=success,
                feedback_score=feedback_score,
                total_interactions=session.total_interactions
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error("Failed to process training interaction", error=str(e))
            return {"error": str(e)}
    
    async def create_ab_test(
        self,
        tenant_id: uuid.UUID,
        name: str,
        description: str,
        strategy_a: ResponseStrategy,
        strategy_b: ResponseStrategy,
        traffic_split: float = 0.5,
        success_metric: str = "transfer_rate",
        target_sample_size: int = 100,
        duration_days: int = 7
    ) -> ABTestConfiguration:
        """
        Create an A/B test for response strategies.
        
        Args:
            tenant_id: Tenant ID
            name: Test name
            description: Test description
            strategy_a: First strategy to test
            strategy_b: Second strategy to test
            traffic_split: Percentage for strategy A (0.0-1.0)
            success_metric: Metric to optimize
            target_sample_size: Target number of interactions
            duration_days: Test duration in days
            
        Returns:
            ABTestConfiguration object
        """
        try:
            test_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            test_config = ABTestConfiguration(
                id=test_id,
                name=name,
                description=description,
                tenant_id=tenant_id,
                status=TestStatus.DRAFT,
                strategy_a=strategy_a,
                strategy_b=strategy_b,
                traffic_split=traffic_split,
                success_metric=success_metric,
                target_sample_size=target_sample_size,
                start_date=current_time,
                end_date=current_time + timedelta(days=duration_days),
                created_at=current_time,
                updated_at=current_time
            )
            
            self.ab_tests[test_id] = test_config
            
            # Store in database
            await self._store_ab_test_in_database(test_config)
            
            self.logger.info(
                "A/B test created",
                test_id=test_id,
                tenant_id=str(tenant_id),
                name=name,
                strategy_a=strategy_a.value,
                strategy_b=strategy_b.value,
                traffic_split=traffic_split
            )
            
            return test_config
            
        except Exception as e:
            self.logger.error("Failed to create A/B test", error=str(e))
            raise
    
    async def start_ab_test(
        self,
        test_id: str,
        tenant_id: uuid.UUID
    ) -> bool:
        """
        Start an A/B test.
        
        Args:
            test_id: Test ID
            tenant_id: Tenant ID for security
            
        Returns:
            True if started successfully
        """
        try:
            if test_id not in self.ab_tests:
                return False
            
            test_config = self.ab_tests[test_id]
            
            # Verify tenant ownership
            if test_config.tenant_id != tenant_id:
                return False
            
            # Update status
            test_config.status = TestStatus.ACTIVE
            test_config.start_date = datetime.utcnow()
            test_config.updated_at = datetime.utcnow()
            
            # Update in database
            await self._update_ab_test_in_database(test_config)
            
            self.logger.info(
                "A/B test started",
                test_id=test_id,
                tenant_id=str(tenant_id),
                name=test_config.name
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to start A/B test", error=str(e))
            return False
    
    async def get_ab_test_results(
        self,
        test_id: str,
        tenant_id: uuid.UUID
    ) -> Optional[Dict[str, ABTestResult]]:
        """
        Get A/B test results and analysis.
        
        Args:
            test_id: Test ID
            tenant_id: Tenant ID for security
            
        Returns:
            Dict with results for both strategies or None
        """
        try:
            if test_id not in self.ab_tests:
                return None
            
            test_config = self.ab_tests[test_id]
            
            # Verify tenant ownership
            if test_config.tenant_id != tenant_id:
                return None
            
            # Collect results from database
            results_a = await self._collect_ab_test_results(
                test_id, test_config.strategy_a, tenant_id
            )
            results_b = await self._collect_ab_test_results(
                test_id, test_config.strategy_b, tenant_id
            )
            
            # Calculate statistical significance
            significance_a = self._calculate_statistical_significance(results_a, results_b)
            significance_b = self._calculate_statistical_significance(results_b, results_a)
            
            results_a.statistical_significance = significance_a
            results_b.statistical_significance = significance_b
            
            return {
                "strategy_a": results_a,
                "strategy_b": results_b
            }
            
        except Exception as e:
            self.logger.error("Failed to get A/B test results", error=str(e))
            return None
    
    async def select_response_strategy(
        self,
        tenant_id: uuid.UUID,
        context: Dict[str, Any]
    ) -> ResponseStrategy:
        """
        Select the appropriate response strategy based on active tests and configuration.
        
        Args:
            tenant_id: Tenant ID
            context: Call context information
            
        Returns:
            Selected ResponseStrategy
        """
        try:
            # Check for active A/B tests
            active_tests = [
                test for test in self.ab_tests.values()
                if (test.tenant_id == tenant_id and 
                    test.status == TestStatus.ACTIVE and
                    datetime.utcnow() <= test.end_date)
            ]
            
            if active_tests:
                # Use the first active test (in production, might have priority logic)
                test = active_tests[0]
                
                # Determine which strategy to use based on traffic split
                import random
                if random.random() < test.traffic_split:
                    selected_strategy = test.strategy_a
                else:
                    selected_strategy = test.strategy_b
                
                # Log the selection for analysis
                await self._log_strategy_selection(
                    test.id, selected_strategy, context
                )
                
                return selected_strategy
            
            # Check for custom scripts that match context
            matching_scripts = await self._find_matching_scripts(tenant_id, context)
            
            if matching_scripts:
                # Use the highest priority script
                script = max(matching_scripts, key=lambda x: x.priority)
                return script.strategy
            
            # Default strategy
            return ResponseStrategy.DEFAULT
            
        except Exception as e:
            self.logger.error("Failed to select response strategy", error=str(e))
            return ResponseStrategy.DEFAULT
    
    async def generate_response_with_strategy(
        self,
        strategy: ResponseStrategy,
        response_type: str,
        variables: Dict[str, Any],
        tenant_id: uuid.UUID
    ) -> str:
        """
        Generate a response using the specified strategy.
        
        Args:
            strategy: Response strategy to use
            response_type: Type of response (greeting, transfer, etc.)
            variables: Variables to substitute
            tenant_id: Tenant ID
            
        Returns:
            Generated response text
        """
        try:
            # Get template for strategy and response type
            template = self.response_templates.get(strategy, {}).get(response_type)
            
            if not template:
                # Fallback to default strategy
                template = self.response_templates[ResponseStrategy.DEFAULT].get(response_type, "")
            
            # Substitute variables
            response = template.format(**variables)
            
            # Enhance with AI if needed
            if strategy in [ResponseStrategy.EMPATHETIC, ResponseStrategy.TECHNICAL]:
                response = await self._enhance_response_with_ai(
                    response, strategy, variables, tenant_id
                )
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to generate response with strategy", error=str(e))
            return "I apologize, but I'm having trouble processing your request right now."
    
    async def get_training_analytics(
        self,
        tenant_id: uuid.UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get training analytics and insights.
        
        Args:
            tenant_id: Tenant ID
            days: Number of days to analyze
            
        Returns:
            Dict containing training analytics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get training sessions
            sessions = [
                session for session in self.active_training_sessions.values()
                if (session.tenant_id == tenant_id and 
                    session.start_time > cutoff_date)
            ]
            
            # Calculate metrics
            total_sessions = len(sessions)
            total_interactions = sum(s.total_interactions for s in sessions)
            successful_interactions = sum(s.successful_interactions for s in sessions)
            
            success_rate = (successful_interactions / total_interactions) if total_interactions > 0 else 0
            
            # Get feedback scores
            all_feedback = []
            for session in sessions:
                all_feedback.extend(session.feedback_scores)
            
            avg_feedback = sum(all_feedback) / len(all_feedback) if all_feedback else 0
            
            # Get A/B test performance
            ab_test_results = []
            for test in self.ab_tests.values():
                if test.tenant_id == tenant_id and test.status == TestStatus.ACTIVE:
                    results = await self.get_ab_test_results(test.id, tenant_id)
                    if results:
                        ab_test_results.append({
                            "test_name": test.name,
                            "results": results
                        })
            
            return {
                "period": {
                    "days": days,
                    "start_date": cutoff_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                },
                "training_sessions": {
                    "total_sessions": total_sessions,
                    "total_interactions": total_interactions,
                    "successful_interactions": successful_interactions,
                    "success_rate": success_rate,
                    "average_feedback_score": avg_feedback
                },
                "ab_tests": ab_test_results,
                "improvements_identified": [
                    improvement for session in sessions
                    for improvement in session.improvements_identified
                ],
                "custom_scripts": len([
                    script for script in self.custom_scripts.values()
                    if script.tenant_id == tenant_id and script.enabled
                ])
            }
            
        except Exception as e:
            self.logger.error("Failed to get training analytics", error=str(e))
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _store_script_in_database(self, script: CustomResponseScript):
        """Store custom script in database."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(script.tenant_id))
                
                # Store in knowledge_base table (reusing existing structure)
                kb_entry = KnowledgeBase(
                    tenant_id=script.tenant_id,
                    question=" ".join(script.trigger_keywords),
                    answer=script.response_template,
                    category="custom_script",
                    confidence_score=0.9,
                    metadata={
                        "script_id": script.id,
                        "name": script.name,
                        "description": script.description,
                        "strategy": script.strategy.value,
                        "variables": script.variables,
                        "priority": script.priority
                    }
                )
                
                session.add(kb_entry)
                await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to store script in database", error=str(e))
    
    async def _update_script_in_database(self, script: CustomResponseScript):
        """Update custom script in database."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(script.tenant_id))
                
                # Update knowledge_base entry
                stmt = (
                    update(KnowledgeBase)
                    .where(
                        and_(
                            KnowledgeBase.tenant_id == script.tenant_id,
                            KnowledgeBase.metadata["script_id"].astext == script.id
                        )
                    )
                    .values(
                        question=" ".join(script.trigger_keywords),
                        answer=script.response_template,
                        metadata={
                            "script_id": script.id,
                            "name": script.name,
                            "description": script.description,
                            "strategy": script.strategy.value,
                            "variables": script.variables,
                            "priority": script.priority
                        },
                        updated_at=script.updated_at
                    )
                )
                
                await session.execute(stmt)
                await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to update script in database", error=str(e))
    
    async def _store_ab_test_in_database(self, test_config: ABTestConfiguration):
        """Store A/B test configuration in database."""
        # Implementation would store in a dedicated ab_tests table
        pass
    
    async def _update_ab_test_in_database(self, test_config: ABTestConfiguration):
        """Update A/B test configuration in database."""
        # Implementation would update the ab_tests table
        pass
    
    async def _analyze_training_interaction(
        self,
        user_input: str,
        ai_response: str,
        success: bool,
        feedback_score: Optional[float],
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze training interaction for improvements."""
        improvements = []
        
        # Simple analysis logic (would be more sophisticated in production)
        if not success:
            if len(ai_response) < 20:
                improvements.append("Response too short - consider more detailed responses")
            
            if "sorry" not in ai_response.lower() and feedback_score and feedback_score < 3:
                improvements.append("Consider adding empathetic language for better user experience")
        
        if feedback_score and feedback_score >= 4:
            improvements.append("High-quality interaction - consider using as training example")
        
        return {
            "success": success,
            "feedback_score": feedback_score,
            "improvements": improvements,
            "response_length": len(ai_response),
            "user_input_length": len(user_input)
        }
    
    async def _generate_enhanced_response(
        self,
        script_id: str,
        user_input: str,
        tenant_id: uuid.UUID
    ) -> str:
        """Generate enhanced response using custom script."""
        if script_id not in self.custom_scripts:
            return "Script not found"
        
        script = self.custom_scripts[script_id]
        
        # Simple template substitution (would be more sophisticated)
        variables = script.variables.copy()
        variables.update({
            "user_input": user_input,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        try:
            return script.response_template.format(**variables)
        except KeyError as e:
            return f"Template error: missing variable {e}"
    
    async def _collect_ab_test_results(
        self,
        test_id: str,
        strategy: ResponseStrategy,
        tenant_id: uuid.UUID
    ) -> ABTestResult:
        """Collect A/B test results for a strategy."""
        # Mock results (would query actual call data)
        import random
        
        sample_size = random.randint(50, 200)
        success_rate = random.uniform(0.6, 0.9)
        
        return ABTestResult(
            test_id=test_id,
            strategy=strategy,
            sample_size=sample_size,
            success_rate=success_rate,
            average_response_time=random.uniform(200, 800),
            transfer_rate=random.uniform(0.3, 0.7),
            satisfaction_score=random.uniform(3.5, 4.8),
            confidence_interval=(success_rate - 0.05, success_rate + 0.05),
            statistical_significance=sample_size > 100
        )
    
    def _calculate_statistical_significance(
        self,
        results_a: ABTestResult,
        results_b: ABTestResult
    ) -> bool:
        """Calculate statistical significance between two results."""
        # Simplified significance test (would use proper statistical methods)
        return (
            abs(results_a.success_rate - results_b.success_rate) > 0.05 and
            results_a.sample_size > 30 and
            results_b.sample_size > 30
        )
    
    async def _find_matching_scripts(
        self,
        tenant_id: uuid.UUID,
        context: Dict[str, Any]
    ) -> List[CustomResponseScript]:
        """Find custom scripts that match the context."""
        matching_scripts = []
        
        for script in self.custom_scripts.values():
            if (script.tenant_id == tenant_id and 
                script.enabled and
                self._script_matches_context(script, context)):
                matching_scripts.append(script)
        
        return matching_scripts
    
    def _script_matches_context(
        self,
        script: CustomResponseScript,
        context: Dict[str, Any]
    ) -> bool:
        """Check if script matches the current context."""
        # Simple keyword matching (would be more sophisticated)
        user_input = context.get("user_input", "").lower()
        
        for keyword in script.trigger_keywords:
            if keyword.lower() in user_input:
                return True
        
        return False
    
    async def _log_strategy_selection(
        self,
        test_id: str,
        strategy: ResponseStrategy,
        context: Dict[str, Any]
    ):
        """Log strategy selection for A/B test analysis."""
        # Implementation would log to database for analysis
        pass
    
    async def _enhance_response_with_ai(
        self,
        base_response: str,
        strategy: ResponseStrategy,
        variables: Dict[str, Any],
        tenant_id: uuid.UUID
    ) -> str:
        """Enhance response using AI based on strategy."""
        try:
            # Use OpenAI to enhance the response based on strategy
            enhancement_prompt = f"""
            Enhance this response to be more {strategy.value}:
            Original: {base_response}
            Context: {variables}
            
            Make it sound more {strategy.value} while keeping it professional and helpful.
            """
            
            # This would call OpenAI API (simplified for now)
            return base_response  # Return original for now
            
        except Exception as e:
            self.logger.error("Failed to enhance response with AI", error=str(e))
            return base_response


# Singleton instance
ai_training_service = AITrainingService()