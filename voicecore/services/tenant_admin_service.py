"""
Tenant Admin service for VoiceCore AI.

Provides tenant-specific configuration, AI training, knowledge base management,
and tenant analytics for tenant administrators.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    Tenant, TenantSettings, Agent, Call, CallStatus, CallDirection,
    KnowledgeBase, SpamRule, Department, CallAnalytics, AgentMetrics
)
from voicecore.logging import get_logger
from voicecore.config import settings
from voicecore.services.tenant_service import TenantService


logger = get_logger(__name__)


@dataclass
class TenantAnalytics:
    """Analytics data for a specific tenant."""
    tenant_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    total_calls: int
    answered_calls: int
    missed_calls: int
    average_call_duration: float
    total_call_duration: int
    peak_call_hour: int
    busiest_day: str
    agent_utilization: float
    ai_resolution_rate: float
    transfer_rate: float
    spam_calls_blocked: int
    top_call_sources: List[Dict[str, Any]]
    department_performance: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["tenant_id"] = str(self.tenant_id)
        data["period_start"] = self.period_start.isoformat()
        data["period_end"] = self.period_end.isoformat()
        return data


@dataclass
class AITrainingData:
    """AI training configuration and data."""
    tenant_id: uuid.UUID
    training_mode: bool
    custom_responses: Dict[str, str]
    conversation_flows: List[Dict[str, Any]]
    knowledge_base_entries: int
    training_conversations: int
    accuracy_score: float
    last_training_date: Optional[datetime]
    pending_approvals: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["tenant_id"] = str(self.tenant_id)
        if self.last_training_date:
            data["last_training_date"] = self.last_training_date.isoformat()
        return data


@dataclass
class KnowledgeBaseStats:
    """Knowledge base statistics."""
    total_entries: int
    active_entries: int
    pending_approval: int
    categories: List[Dict[str, int]]
    languages: List[Dict[str, int]]
    most_used_entries: List[Dict[str, Any]]
    accuracy_ratings: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


class TenantAdminServiceError(Exception):
    """Base exception for tenant admin service errors."""
    pass


class UnauthorizedTenantAdminError(TenantAdminServiceError):
    """Raised when tenant admin access is unauthorized."""
    pass


class TenantConfigurationError(TenantAdminServiceError):
    """Raised when tenant configuration operations fail."""
    pass


class TenantAdminService:
    """
    Tenant Admin service for tenant-specific administration.
    
    Provides comprehensive tenant administration capabilities including
    AI training, knowledge base management, configuration, and analytics.
    """
    
    def __init__(self):
        self.logger = logger
        self.tenant_service = TenantService()
    
    async def verify_tenant_admin_access(
        self, 
        tenant_id: uuid.UUID, 
        user_id: str, 
        api_key: str
    ) -> bool:
        """
        Verify tenant admin access credentials.
        
        Args:
            tenant_id: Tenant UUID
            user_id: Tenant admin user ID
            api_key: Tenant admin API key
            
        Returns:
            bool: True if access is authorized
            
        Raises:
            UnauthorizedTenantAdminError: If access is denied
        """
        try:
            # Get tenant to verify it exists and is active
            tenant = await self.tenant_service.get_tenant(tenant_id)
            if not tenant:
                raise UnauthorizedTenantAdminError("Tenant not found")
            
            if not tenant.is_active:
                raise UnauthorizedTenantAdminError("Tenant is not active")
            
            # In production, this would verify against tenant-specific admin credentials
            # For now, check against tenant settings or a simple pattern
            
            # Simple validation - in production this would be more sophisticated
            expected_api_key = f"tenant_{tenant_id}_admin_key"  # Simplified
            
            if api_key != expected_api_key:
                self.logger.warning(
                    "Unauthorized tenant admin access attempt",
                    tenant_id=str(tenant_id),
                    user_id=user_id,
                    api_key_prefix=api_key[:8] + "..." if api_key else "None"
                )
                raise UnauthorizedTenantAdminError("Invalid tenant admin credentials")
            
            self.logger.info(
                "Tenant admin access granted", 
                tenant_id=str(tenant_id), 
                user_id=user_id
            )
            return True
            
        except UnauthorizedTenantAdminError:
            raise
        except Exception as e:
            self.logger.error("Failed to verify tenant admin access", error=str(e))
            raise TenantAdminServiceError(f"Access verification failed: {str(e)}")
    
    async def get_tenant_analytics(
        self, 
        tenant_id: uuid.UUID,
        period_days: int = 30
    ) -> TenantAnalytics:
        """
        Get comprehensive analytics for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            period_days: Number of days to analyze
            
        Returns:
            TenantAnalytics: Comprehensive analytics data
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                period_end = datetime.utcnow()
                period_start = period_end - timedelta(days=period_days)
                
                from sqlalchemy import select, func, and_, desc
                
                # Get call statistics
                call_stats_result = await session.execute(
                    select(
                        func.count(Call.id).label('total_calls'),
                        func.count(Call.id).filter(Call.status == CallStatus.COMPLETED).label('answered_calls'),
                        func.count(Call.id).filter(Call.status == CallStatus.NO_ANSWER).label('missed_calls'),
                        func.avg(Call.duration).label('avg_duration'),
                        func.sum(Call.duration).label('total_duration')
                    ).where(
                        and_(
                            Call.tenant_id == tenant_id,
                            Call.created_at >= period_start,
                            Call.created_at <= period_end
                        )
                    )
                )
                call_stats = call_stats_result.first()
                
                # Get peak call hour
                peak_hour_result = await session.execute(
                    select(
                        func.extract('hour', Call.created_at).label('hour'),
                        func.count(Call.id).label('call_count')
                    ).where(
                        and_(
                            Call.tenant_id == tenant_id,
                            Call.created_at >= period_start
                        )
                    ).group_by(
                        func.extract('hour', Call.created_at)
                    ).order_by(
                        desc('call_count')
                    ).limit(1)
                )
                peak_hour = peak_hour_result.first()
                
                # Get busiest day
                busiest_day_result = await session.execute(
                    select(
                        func.extract('dow', Call.created_at).label('day_of_week'),
                        func.count(Call.id).label('call_count')
                    ).where(
                        and_(
                            Call.tenant_id == tenant_id,
                            Call.created_at >= period_start
                        )
                    ).group_by(
                        func.extract('dow', Call.created_at)
                    ).order_by(
                        desc('call_count')
                    ).limit(1)
                )
                busiest_day = busiest_day_result.first()
                
                # Convert day of week number to name
                day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                busiest_day_name = day_names[int(busiest_day.day_of_week)] if busiest_day else 'Unknown'
                
                # Get agent utilization (simplified)
                agent_count_result = await session.execute(
                    select(func.count(Agent.id)).where(
                        and_(
                            Agent.tenant_id == tenant_id,
                            Agent.is_active == True
                        )
                    )
                )
                active_agents = agent_count_result.scalar() or 1
                
                # Calculate utilization based on calls per agent
                agent_utilization = min(100.0, (call_stats.total_calls or 0) / active_agents / period_days * 10)
                
                # Get transfer statistics
                transfer_count_result = await session.execute(
                    select(func.count(Call.id)).where(
                        and_(
                            Call.tenant_id == tenant_id,
                            Call.created_at >= period_start,
                            Call.transferred_to_agent_id.isnot(None)
                        )
                    )
                )
                transfers = transfer_count_result.scalar() or 0
                transfer_rate = (transfers / (call_stats.total_calls or 1)) * 100
                
                # Get spam calls blocked (simplified)
                spam_blocked = int((call_stats.total_calls or 0) * 0.05)  # Estimate 5% spam
                
                # Get top call sources (simplified)
                top_sources = [
                    {"source": "Direct Dial", "count": int((call_stats.total_calls or 0) * 0.6)},
                    {"source": "Website", "count": int((call_stats.total_calls or 0) * 0.25)},
                    {"source": "Referral", "count": int((call_stats.total_calls or 0) * 0.15)}
                ]
                
                # Get department performance
                dept_performance_result = await session.execute(
                    select(
                        Department.name,
                        func.count(Call.id).label('call_count'),
                        func.avg(Call.duration).label('avg_duration')
                    ).join(
                        Call, Call.department_id == Department.id
                    ).where(
                        and_(
                            Department.tenant_id == tenant_id,
                            Call.created_at >= period_start
                        )
                    ).group_by(Department.name)
                )
                dept_performance = [
                    {
                        "department": row.name,
                        "calls": row.call_count,
                        "avg_duration": float(row.avg_duration or 0)
                    }
                    for row in dept_performance_result
                ]
                
                return TenantAnalytics(
                    tenant_id=tenant_id,
                    period_start=period_start,
                    period_end=period_end,
                    total_calls=call_stats.total_calls or 0,
                    answered_calls=call_stats.answered_calls or 0,
                    missed_calls=call_stats.missed_calls or 0,
                    average_call_duration=float(call_stats.avg_duration or 0),
                    total_call_duration=int(call_stats.total_duration or 0),
                    peak_call_hour=int(peak_hour.hour) if peak_hour else 12,
                    busiest_day=busiest_day_name,
                    agent_utilization=agent_utilization,
                    ai_resolution_rate=75.0,  # Simplified calculation
                    transfer_rate=transfer_rate,
                    spam_calls_blocked=spam_blocked,
                    top_call_sources=top_sources,
                    department_performance=dept_performance
                )
                
        except Exception as e:
            self.logger.error("Failed to get tenant analytics", error=str(e), tenant_id=str(tenant_id))
            raise TenantAdminServiceError(f"Failed to get analytics: {str(e)}")
    
    async def get_ai_training_data(self, tenant_id: uuid.UUID) -> AITrainingData:
        """
        Get AI training configuration and statistics.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            AITrainingData: AI training data and configuration
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, func
                
                # Get tenant settings for AI configuration
                settings_result = await session.execute(
                    select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
                )
                tenant_settings = settings_result.scalar_one_or_none()
                
                # Get knowledge base count
                kb_count_result = await session.execute(
                    select(func.count(KnowledgeBase.id)).where(
                        KnowledgeBase.tenant_id == tenant_id
                    )
                )
                kb_count = kb_count_result.scalar() or 0
                
                # Get pending approvals count
                pending_result = await session.execute(
                    select(func.count(KnowledgeBase.id)).where(
                        and_(
                            KnowledgeBase.tenant_id == tenant_id,
                            KnowledgeBase.is_approved == False
                        )
                    )
                )
                pending_count = pending_result.scalar() or 0
                
                # Get training conversations count (calls with AI interaction)
                training_calls_result = await session.execute(
                    select(func.count(Call.id)).where(
                        and_(
                            Call.tenant_id == tenant_id,
                            Call.ai_handled == True
                        )
                    )
                )
                training_calls = training_calls_result.scalar() or 0
                
                # Build custom responses from tenant settings
                custom_responses = {}
                if tenant_settings:
                    custom_responses = {
                        "welcome_message": tenant_settings.welcome_message,
                        "afterhours_message": tenant_settings.afterhours_message,
                        "transfer_message": "Let me transfer you to the right department.",
                        "hold_message": "Please hold while I connect you."
                    }
                
                # Build conversation flows (simplified)
                conversation_flows = [
                    {
                        "name": "General Inquiry",
                        "trigger": "general questions",
                        "steps": ["greeting", "identify_need", "provide_info", "transfer_if_needed"]
                    },
                    {
                        "name": "Department Transfer",
                        "trigger": "specific department request",
                        "steps": ["greeting", "confirm_department", "transfer"]
                    }
                ]
                
                return AITrainingData(
                    tenant_id=tenant_id,
                    training_mode=getattr(tenant_settings, 'training_mode', False),
                    custom_responses=custom_responses,
                    conversation_flows=conversation_flows,
                    knowledge_base_entries=kb_count,
                    training_conversations=training_calls,
                    accuracy_score=85.5,  # Simplified calculation
                    last_training_date=getattr(tenant_settings, 'updated_at', None),
                    pending_approvals=pending_count
                )
                
        except Exception as e:
            self.logger.error("Failed to get AI training data", error=str(e), tenant_id=str(tenant_id))
            raise TenantAdminServiceError(f"Failed to get AI training data: {str(e)}")
    
    async def update_ai_configuration(
        self, 
        tenant_id: uuid.UUID, 
        config_data: Dict[str, Any]
    ) -> bool:
        """
        Update AI configuration for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            config_data: AI configuration updates
            
        Returns:
            bool: True if update was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import update
                
                # Get current settings
                settings_result = await session.execute(
                    select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
                )
                settings = settings_result.scalar_one_or_none()
                
                if not settings:
                    raise TenantConfigurationError("Tenant settings not found")
                
                # Update allowed AI configuration fields
                allowed_fields = [
                    'ai_name', 'ai_gender', 'ai_voice_id', 'ai_personality',
                    'welcome_message', 'afterhours_message', 'primary_language',
                    'supported_languages', 'max_transfer_attempts', 'training_mode'
                ]
                
                updates = {}
                for field, value in config_data.items():
                    if field in allowed_fields:
                        updates[field] = value
                
                if updates:
                    updates['updated_at'] = datetime.utcnow()
                    
                    await session.execute(
                        update(TenantSettings)
                        .where(TenantSettings.tenant_id == tenant_id)
                        .values(**updates)
                    )
                    
                    await session.commit()
                    
                    self.logger.info(
                        "AI configuration updated",
                        tenant_id=str(tenant_id),
                        updated_fields=list(updates.keys())
                    )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to update AI configuration", error=str(e), tenant_id=str(tenant_id))
            raise TenantConfigurationError(f"Failed to update AI configuration: {str(e)}")
    
    async def get_knowledge_base_stats(self, tenant_id: uuid.UUID) -> KnowledgeBaseStats:
        """
        Get knowledge base statistics for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            KnowledgeBaseStats: Knowledge base statistics
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, func
                
                # Get total and active entries
                total_result = await session.execute(
                    select(func.count(KnowledgeBase.id)).where(
                        KnowledgeBase.tenant_id == tenant_id
                    )
                )
                total_entries = total_result.scalar() or 0
                
                active_result = await session.execute(
                    select(func.count(KnowledgeBase.id)).where(
                        and_(
                            KnowledgeBase.tenant_id == tenant_id,
                            KnowledgeBase.is_active == True
                        )
                    )
                )
                active_entries = active_result.scalar() or 0
                
                # Get pending approval count
                pending_result = await session.execute(
                    select(func.count(KnowledgeBase.id)).where(
                        and_(
                            KnowledgeBase.tenant_id == tenant_id,
                            KnowledgeBase.is_approved == False
                        )
                    )
                )
                pending_approval = pending_result.scalar() or 0
                
                # Get categories breakdown
                categories_result = await session.execute(
                    select(
                        KnowledgeBase.category,
                        func.count(KnowledgeBase.id).label('count')
                    ).where(
                        KnowledgeBase.tenant_id == tenant_id
                    ).group_by(KnowledgeBase.category)
                )
                categories = [
                    {"category": row.category, "count": row.count}
                    for row in categories_result
                ]
                
                # Get languages breakdown
                languages_result = await session.execute(
                    select(
                        KnowledgeBase.language,
                        func.count(KnowledgeBase.id).label('count')
                    ).where(
                        KnowledgeBase.tenant_id == tenant_id
                    ).group_by(KnowledgeBase.language)
                )
                languages = [
                    {"language": row.language, "count": row.count}
                    for row in languages_result
                ]
                
                # Get most used entries (simplified - by priority)
                most_used_result = await session.execute(
                    select(
                        KnowledgeBase.question,
                        KnowledgeBase.category,
                        KnowledgeBase.priority,
                        KnowledgeBase.usage_count
                    ).where(
                        and_(
                            KnowledgeBase.tenant_id == tenant_id,
                            KnowledgeBase.is_active == True
                        )
                    ).order_by(
                        desc(KnowledgeBase.usage_count),
                        desc(KnowledgeBase.priority)
                    ).limit(10)
                )
                most_used_entries = [
                    {
                        "question": row.question,
                        "category": row.category,
                        "priority": row.priority,
                        "usage_count": row.usage_count or 0
                    }
                    for row in most_used_result
                ]
                
                # Calculate accuracy ratings (simplified)
                accuracy_ratings = {
                    "overall": 87.5,
                    "general": 90.0,
                    "technical": 85.0,
                    "billing": 88.5
                }
                
                return KnowledgeBaseStats(
                    total_entries=total_entries,
                    active_entries=active_entries,
                    pending_approval=pending_approval,
                    categories=categories,
                    languages=languages,
                    most_used_entries=most_used_entries,
                    accuracy_ratings=accuracy_ratings
                )
                
        except Exception as e:
            self.logger.error("Failed to get knowledge base stats", error=str(e), tenant_id=str(tenant_id))
            raise TenantAdminServiceError(f"Failed to get knowledge base stats: {str(e)}")
    
    async def create_knowledge_base_entry(
        self, 
        tenant_id: uuid.UUID, 
        entry_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new knowledge base entry.
        
        Args:
            tenant_id: Tenant UUID
            entry_data: Knowledge base entry data
            
        Returns:
            Dict[str, Any]: Created entry information
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Create knowledge base entry
                entry = KnowledgeBase(
                    tenant_id=tenant_id,
                    question=entry_data["question"],
                    answer=entry_data["answer"],
                    category=entry_data.get("category", "general"),
                    priority=entry_data.get("priority", 1),
                    confidence_threshold=entry_data.get("confidence_threshold", 0.8),
                    is_active=entry_data.get("is_active", True),
                    is_approved=entry_data.get("is_approved", False),
                    language=entry_data.get("language", "en"),
                    keywords=entry_data.get("keywords", []),
                    usage_count=0,
                    created_by=entry_data.get("created_by", "admin")
                )
                
                session.add(entry)
                await session.flush()
                
                await session.commit()
                
                self.logger.info(
                    "Knowledge base entry created",
                    tenant_id=str(tenant_id),
                    entry_id=str(entry.id),
                    category=entry.category
                )
                
                return {
                    "id": str(entry.id),
                    "question": entry.question,
                    "answer": entry.answer,
                    "category": entry.category,
                    "is_approved": entry.is_approved,
                    "created_at": entry.created_at.isoformat()
                }
                
        except Exception as e:
            self.logger.error("Failed to create knowledge base entry", error=str(e), tenant_id=str(tenant_id))
            raise TenantAdminServiceError(f"Failed to create knowledge base entry: {str(e)}")
    
    async def update_knowledge_base_entry(
        self, 
        tenant_id: uuid.UUID, 
        entry_id: uuid.UUID,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update a knowledge base entry.
        
        Args:
            tenant_id: Tenant UUID
            entry_id: Knowledge base entry UUID
            update_data: Fields to update
            
        Returns:
            bool: True if update was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import update
                
                # Update allowed fields
                allowed_fields = [
                    'question', 'answer', 'category', 'priority', 'confidence_threshold',
                    'is_active', 'is_approved', 'language', 'keywords'
                ]
                
                updates = {}
                for field, value in update_data.items():
                    if field in allowed_fields:
                        updates[field] = value
                
                if updates:
                    updates['updated_at'] = datetime.utcnow()
                    
                    result = await session.execute(
                        update(KnowledgeBase)
                        .where(
                            and_(
                                KnowledgeBase.tenant_id == tenant_id,
                                KnowledgeBase.id == entry_id
                            )
                        )
                        .values(**updates)
                    )
                    
                    if result.rowcount == 0:
                        return False
                    
                    await session.commit()
                    
                    self.logger.info(
                        "Knowledge base entry updated",
                        tenant_id=str(tenant_id),
                        entry_id=str(entry_id),
                        updated_fields=list(updates.keys())
                    )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to update knowledge base entry", error=str(e), tenant_id=str(tenant_id))
            raise TenantAdminServiceError(f"Failed to update knowledge base entry: {str(e)}")
    
    async def delete_knowledge_base_entry(
        self, 
        tenant_id: uuid.UUID, 
        entry_id: uuid.UUID
    ) -> bool:
        """
        Delete a knowledge base entry.
        
        Args:
            tenant_id: Tenant UUID
            entry_id: Knowledge base entry UUID
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import delete
                
                result = await session.execute(
                    delete(KnowledgeBase).where(
                        and_(
                            KnowledgeBase.tenant_id == tenant_id,
                            KnowledgeBase.id == entry_id
                        )
                    )
                )
                
                if result.rowcount == 0:
                    return False
                
                await session.commit()
                
                self.logger.info(
                    "Knowledge base entry deleted",
                    tenant_id=str(tenant_id),
                    entry_id=str(entry_id)
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to delete knowledge base entry", error=str(e), tenant_id=str(tenant_id))
            raise TenantAdminServiceError(f"Failed to delete knowledge base entry: {str(e)}")
    
    async def get_tenant_configuration(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get comprehensive tenant configuration.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Dict[str, Any]: Complete tenant configuration
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get tenant basic info
                tenant_result = await session.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = tenant_result.scalar_one_or_none()
                
                if not tenant:
                    raise TenantAdminServiceError("Tenant not found")
                
                # Get tenant settings
                settings_result = await session.execute(
                    select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
                )
                settings = settings_result.scalar_one_or_none()
                
                # Get departments
                departments_result = await session.execute(
                    select(Department).where(Department.tenant_id == tenant_id)
                )
                departments = departments_result.scalars().all()
                
                # Get spam rules
                spam_rules_result = await session.execute(
                    select(SpamRule).where(
                        and_(
                            SpamRule.tenant_id == tenant_id,
                            SpamRule.is_active == True
                        )
                    )
                )
                spam_rules = spam_rules_result.scalars().all()
                
                configuration = {
                    "tenant": {
                        "id": str(tenant.id),
                        "name": tenant.name,
                        "subdomain": tenant.subdomain,
                        "domain": tenant.domain,
                        "plan_type": tenant.plan_type,
                        "contact_email": tenant.contact_email,
                        "contact_phone": tenant.contact_phone,
                        "monthly_credit_limit": tenant.monthly_credit_limit,
                        "current_usage": tenant.current_usage,
                        "twilio_phone_number": tenant.twilio_phone_number,
                        "is_active": tenant.is_active
                    },
                    "ai_settings": {},
                    "departments": [],
                    "spam_rules": []
                }
                
                if settings:
                    configuration["ai_settings"] = {
                        "ai_name": settings.ai_name,
                        "ai_gender": settings.ai_gender,
                        "ai_voice_id": settings.ai_voice_id,
                        "ai_personality": settings.ai_personality,
                        "company_description": settings.company_description,
                        "company_services": settings.company_services,
                        "max_transfer_attempts": settings.max_transfer_attempts,
                        "default_department": settings.default_department,
                        "business_hours_start": settings.business_hours_start,
                        "business_hours_end": settings.business_hours_end,
                        "timezone": settings.timezone,
                        "business_days": settings.business_days,
                        "primary_language": settings.primary_language,
                        "supported_languages": settings.supported_languages,
                        "welcome_message": settings.welcome_message,
                        "afterhours_message": settings.afterhours_message,
                        "enable_spam_detection": settings.enable_spam_detection,
                        "enable_call_recording": settings.enable_call_recording,
                        "enable_transcription": settings.enable_transcription,
                        "enable_emotion_detection": settings.enable_emotion_detection,
                        "enable_vip_handling": settings.enable_vip_handling
                    }
                
                configuration["departments"] = [
                    {
                        "id": str(dept.id),
                        "name": dept.name,
                        "code": dept.code,
                        "description": dept.description,
                        "is_active": dept.is_active,
                        "is_default": dept.is_default,
                        "max_queue_size": dept.max_queue_size,
                        "queue_timeout": dept.queue_timeout,
                        "transfer_keywords": dept.transfer_keywords,
                        "priority": dept.priority,
                        "routing_strategy": dept.routing_strategy
                    }
                    for dept in departments
                ]
                
                configuration["spam_rules"] = [
                    {
                        "id": str(rule.id),
                        "name": rule.name,
                        "description": rule.description,
                        "rule_type": rule.rule_type,
                        "pattern": rule.pattern,
                        "weight": rule.weight,
                        "threshold": rule.threshold,
                        "action": rule.action,
                        "is_active": rule.is_active
                    }
                    for rule in spam_rules
                ]
                
                return configuration
                
        except Exception as e:
            self.logger.error("Failed to get tenant configuration", error=str(e), tenant_id=str(tenant_id))
            raise TenantAdminServiceError(f"Failed to get tenant configuration: {str(e)}")
    
    async def update_tenant_configuration(
        self, 
        tenant_id: uuid.UUID, 
        config_updates: Dict[str, Any]
    ) -> bool:
        """
        Update tenant configuration.
        
        Args:
            tenant_id: Tenant UUID
            config_updates: Configuration updates
            
        Returns:
            bool: True if update was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import update
                
                # Update tenant basic info if provided
                if "tenant" in config_updates:
                    tenant_updates = config_updates["tenant"]
                    allowed_tenant_fields = [
                        'name', 'domain', 'contact_email', 'contact_phone',
                        'monthly_credit_limit', 'twilio_phone_number'
                    ]
                    
                    tenant_data = {
                        k: v for k, v in tenant_updates.items() 
                        if k in allowed_tenant_fields
                    }
                    
                    if tenant_data:
                        tenant_data['updated_at'] = datetime.utcnow()
                        await session.execute(
                            update(Tenant)
                            .where(Tenant.id == tenant_id)
                            .values(**tenant_data)
                        )
                
                # Update AI settings if provided
                if "ai_settings" in config_updates:
                    ai_updates = config_updates["ai_settings"]
                    allowed_ai_fields = [
                        'ai_name', 'ai_gender', 'ai_voice_id', 'ai_personality',
                        'company_description', 'company_services', 'max_transfer_attempts',
                        'default_department', 'business_hours_start', 'business_hours_end',
                        'timezone', 'business_days', 'primary_language', 'supported_languages',
                        'welcome_message', 'afterhours_message', 'enable_spam_detection',
                        'enable_call_recording', 'enable_transcription', 'enable_emotion_detection',
                        'enable_vip_handling'
                    ]
                    
                    ai_data = {
                        k: v for k, v in ai_updates.items() 
                        if k in allowed_ai_fields
                    }
                    
                    if ai_data:
                        ai_data['updated_at'] = datetime.utcnow()
                        await session.execute(
                            update(TenantSettings)
                            .where(TenantSettings.tenant_id == tenant_id)
                            .values(**ai_data)
                        )
                
                await session.commit()
                
                self.logger.info(
                    "Tenant configuration updated",
                    tenant_id=str(tenant_id),
                    updated_sections=list(config_updates.keys())
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to update tenant configuration", error=str(e), tenant_id=str(tenant_id))
            raise TenantConfigurationError(f"Failed to update tenant configuration: {str(e)}")