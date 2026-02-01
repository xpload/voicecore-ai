"""
Tenant management service for VoiceCore AI.

Provides comprehensive tenant lifecycle management with proper isolation,
provisioning, and cleanup for the multitenant architecture.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, delete, update, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context, DatabaseManager
from voicecore.models import (
    Tenant, TenantSettings, Department, Agent, Call, 
    KnowledgeBase, SpamRule, CallAnalytics, AgentMetrics
)
from voicecore.config import settings, TenantSettings as TenantConfig
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils


logger = get_logger(__name__)


class TenantServiceError(Exception):
    """Base exception for tenant service errors."""
    pass


class TenantNotFoundError(TenantServiceError):
    """Raised when a tenant is not found."""
    pass


class TenantAlreadyExistsError(TenantServiceError):
    """Raised when trying to create a tenant that already exists."""
    pass


class TenantService:
    """
    Comprehensive tenant management service.
    
    Handles tenant lifecycle including creation, configuration,
    updates, and complete data cleanup with proper isolation.
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.logger = logger
    
    async def create_tenant(self, tenant_data: Dict[str, Any]) -> Tenant:
        """
        Create a new tenant with complete provisioning.
        
        Args:
            tenant_data: Dictionary containing tenant information
            
        Returns:
            Tenant: Created tenant instance
            
        Raises:
            TenantAlreadyExistsError: If tenant already exists
            TenantServiceError: If creation fails
        """
        try:
            async with get_db_session() as session:
                # Check if tenant already exists
                existing_tenant = await self._check_tenant_exists(
                    session, 
                    tenant_data.get("subdomain"), 
                    tenant_data.get("contact_email")
                )
                
                if existing_tenant:
                    raise TenantAlreadyExistsError(
                        f"Tenant already exists with subdomain '{tenant_data.get('subdomain')}' "
                        f"or email '{tenant_data.get('contact_email')}'"
                    )
                
                # Create tenant
                tenant = Tenant(
                    name=tenant_data["name"],
                    subdomain=tenant_data.get("subdomain"),
                    domain=tenant_data.get("domain"),
                    is_active=tenant_data.get("is_active", True),
                    plan_type=tenant_data.get("plan_type", "basic"),
                    contact_email=tenant_data["contact_email"],
                    contact_phone=tenant_data.get("contact_phone"),
                    monthly_credit_limit=tenant_data.get("monthly_credit_limit", 1000),
                    current_usage=0,
                    settings=tenant_data.get("settings", {}),
                    twilio_phone_number=tenant_data.get("twilio_phone_number")
                )
                
                session.add(tenant)
                await session.flush()  # Get the tenant ID
                
                # Set tenant context for subsequent operations
                await set_tenant_context(session, str(tenant.id))
                
                # Create default tenant settings
                await self._create_default_tenant_settings(session, tenant.id)
                
                # Create default departments
                await self._create_default_departments(session, tenant.id)
                
                # Create default knowledge base entries
                await self._create_default_knowledge_base(session, tenant.id)
                
                # Create default spam rules
                await self._create_default_spam_rules(session, tenant.id)
                
                await session.commit()
                
                self.logger.info(
                    "Tenant created successfully",
                    tenant_id=str(tenant.id),
                    tenant_name=tenant.name,
                    subdomain=tenant.subdomain,
                    plan_type=tenant.plan_type
                )
                
                return tenant
                
        except IntegrityError as e:
            self.logger.error("Tenant creation failed due to constraint violation", error=str(e))
            raise TenantAlreadyExistsError("Tenant with this subdomain or email already exists")
        except Exception as e:
            self.logger.error("Tenant creation failed", error=str(e))
            raise TenantServiceError(f"Failed to create tenant: {str(e)}")
    
    async def get_tenant(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        """
        Get tenant by ID.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Optional[Tenant]: Tenant instance or None if not found
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = result.scalar_one_or_none()
                
                if tenant:
                    self.logger.debug("Tenant retrieved", tenant_id=str(tenant_id))
                
                return tenant
                
        except Exception as e:
            self.logger.error("Failed to get tenant", tenant_id=str(tenant_id), error=str(e))
            return None
    
    async def get_tenant_by_subdomain(self, subdomain: str) -> Optional[Tenant]:
        """
        Get tenant by subdomain.
        
        Args:
            subdomain: Tenant subdomain
            
        Returns:
            Optional[Tenant]: Tenant instance or None if not found
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Tenant).where(Tenant.subdomain == subdomain)
                )
                tenant = result.scalar_one_or_none()
                
                if tenant:
                    self.logger.debug("Tenant retrieved by subdomain", subdomain=subdomain)
                
                return tenant
                
        except Exception as e:
            self.logger.error("Failed to get tenant by subdomain", subdomain=subdomain, error=str(e))
            return None
    
    async def list_tenants(
        self, 
        skip: int = 0, 
        limit: int = 100,
        active_only: bool = False
    ) -> List[Tenant]:
        """
        List tenants with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: Whether to return only active tenants
            
        Returns:
            List[Tenant]: List of tenant instances
        """
        try:
            async with get_db_session() as session:
                query = select(Tenant)
                
                if active_only:
                    query = query.where(Tenant.is_active == True)
                
                query = query.offset(skip).limit(limit).order_by(Tenant.created_at.desc())
                
                result = await session.execute(query)
                tenants = result.scalars().all()
                
                self.logger.debug(
                    "Tenants listed",
                    count=len(tenants),
                    skip=skip,
                    limit=limit,
                    active_only=active_only
                )
                
                return list(tenants)
                
        except Exception as e:
            self.logger.error("Failed to list tenants", error=str(e))
            return []
    
    async def update_tenant(
        self, 
        tenant_id: uuid.UUID, 
        update_data: Dict[str, Any]
    ) -> Optional[Tenant]:
        """
        Update tenant information.
        
        Args:
            tenant_id: Tenant UUID
            update_data: Dictionary containing fields to update
            
        Returns:
            Optional[Tenant]: Updated tenant instance or None if not found
            
        Raises:
            TenantNotFoundError: If tenant doesn't exist
            TenantServiceError: If update fails
        """
        try:
            async with get_db_session() as session:
                # Get existing tenant
                result = await session.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = result.scalar_one_or_none()
                
                if not tenant:
                    raise TenantNotFoundError(f"Tenant {tenant_id} not found")
                
                # Update allowed fields
                allowed_fields = [
                    'name', 'domain', 'is_active', 'plan_type', 'contact_email',
                    'contact_phone', 'monthly_credit_limit', 'settings', 'twilio_phone_number'
                ]
                
                for field, value in update_data.items():
                    if field in allowed_fields and hasattr(tenant, field):
                        setattr(tenant, field, value)
                
                tenant.updated_at = datetime.utcnow()
                await session.commit()
                
                self.logger.info(
                    "Tenant updated successfully",
                    tenant_id=str(tenant_id),
                    updated_fields=list(update_data.keys())
                )
                
                return tenant
                
        except TenantNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Tenant update failed", tenant_id=str(tenant_id), error=str(e))
            raise TenantServiceError(f"Failed to update tenant: {str(e)}")
    
    async def delete_tenant(self, tenant_id: uuid.UUID) -> bool:
        """
        Delete tenant and all associated data.
        
        This performs a complete cleanup of all tenant-related data
        across all tables with proper cascade deletion.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            TenantNotFoundError: If tenant doesn't exist
            TenantServiceError: If deletion fails
        """
        try:
            async with get_db_session() as session:
                # Verify tenant exists
                result = await session.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = result.scalar_one_or_none()
                
                if not tenant:
                    raise TenantNotFoundError(f"Tenant {tenant_id} not found")
                
                # Set tenant context for cleanup operations
                await set_tenant_context(session, str(tenant_id))
                
                # Log data counts before deletion for audit
                await self._log_tenant_data_counts(session, tenant_id, "before_deletion")
                
                # Delete tenant (CASCADE will handle related data)
                await session.execute(
                    delete(Tenant).where(Tenant.id == tenant_id)
                )
                
                await session.commit()
                
                # Verify complete cleanup
                await self._verify_tenant_cleanup(session, tenant_id)
                
                self.logger.info(
                    "Tenant deleted successfully",
                    tenant_id=str(tenant_id),
                    tenant_name=tenant.name
                )
                
                return True
                
        except TenantNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Tenant deletion failed", tenant_id=str(tenant_id), error=str(e))
            raise TenantServiceError(f"Failed to delete tenant: {str(e)}")
    
    async def get_tenant_settings(self, tenant_id: uuid.UUID) -> Optional[TenantSettings]:
        """
        Get tenant-specific settings.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Optional[TenantSettings]: Tenant settings or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
                )
                settings = result.scalar_one_or_none()
                
                return settings
                
        except Exception as e:
            self.logger.error("Failed to get tenant settings", tenant_id=str(tenant_id), error=str(e))
            return None
    
    async def update_tenant_settings(
        self, 
        tenant_id: uuid.UUID, 
        settings_data: Dict[str, Any]
    ) -> Optional[TenantSettings]:
        """
        Update tenant-specific settings.
        
        Args:
            tenant_id: Tenant UUID
            settings_data: Dictionary containing settings to update
            
        Returns:
            Optional[TenantSettings]: Updated settings or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
                )
                settings = result.scalar_one_or_none()
                
                if not settings:
                    return None
                
                # Update allowed fields
                for field, value in settings_data.items():
                    if hasattr(settings, field):
                        setattr(settings, field, value)
                
                settings.updated_at = datetime.utcnow()
                await session.commit()
                
                self.logger.info(
                    "Tenant settings updated",
                    tenant_id=str(tenant_id),
                    updated_fields=list(settings_data.keys())
                )
                
                return settings
                
        except Exception as e:
            self.logger.error("Failed to update tenant settings", tenant_id=str(tenant_id), error=str(e))
            return None
    
    async def get_tenant_usage_stats(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get tenant usage statistics.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Dict[str, Any]: Usage statistics
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get basic counts
                stats = {}
                
                # Count agents
                agent_result = await session.execute(
                    "SELECT COUNT(*) FROM agents WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                stats["total_agents"] = agent_result.scalar()
                
                # Count active agents
                active_agent_result = await session.execute(
                    "SELECT COUNT(*) FROM agents WHERE tenant_id = :tenant_id AND is_active = true",
                    {"tenant_id": tenant_id}
                )
                stats["active_agents"] = active_agent_result.scalar()
                
                # Count departments
                dept_result = await session.execute(
                    "SELECT COUNT(*) FROM departments WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                stats["total_departments"] = dept_result.scalar()
                
                # Count calls (last 30 days)
                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                call_result = await session.execute(
                    "SELECT COUNT(*) FROM calls WHERE tenant_id = :tenant_id AND created_at >= :since",
                    {"tenant_id": tenant_id, "since": thirty_days_ago}
                )
                stats["calls_last_30_days"] = call_result.scalar()
                
                # Count knowledge base entries
                kb_result = await session.execute(
                    "SELECT COUNT(*) FROM knowledge_base WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                stats["knowledge_base_entries"] = kb_result.scalar()
                
                # Get current usage from tenant
                tenant_result = await session.execute(
                    "SELECT current_usage, monthly_credit_limit FROM tenants WHERE id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                tenant_data = tenant_result.fetchone()
                if tenant_data:
                    stats["current_usage"] = tenant_data[0]
                    stats["monthly_credit_limit"] = tenant_data[1]
                    stats["usage_percentage"] = (tenant_data[0] / tenant_data[1]) * 100 if tenant_data[1] > 0 else 0
                
                return stats
                
        except Exception as e:
            self.logger.error("Failed to get tenant usage stats", tenant_id=str(tenant_id), error=str(e))
            return {}
    
    # Private helper methods
    
    async def _check_tenant_exists(
        self, 
        session, 
        subdomain: Optional[str], 
        email: str
    ) -> Optional[Tenant]:
        """Check if tenant already exists by subdomain or email."""
        conditions = [Tenant.contact_email == email]
        
        if subdomain:
            conditions.append(Tenant.subdomain == subdomain)
        
        result = await session.execute(
            select(Tenant).where(or_(*conditions))
        )
        return result.scalar_one_or_none()
    
    async def _create_default_tenant_settings(self, session, tenant_id: uuid.UUID):
        """Create default tenant settings."""
        settings = TenantSettings(
            tenant_id=tenant_id,
            ai_name="Sofia",
            ai_gender="female",
            ai_voice_id="alloy",
            ai_personality="Professional, friendly, and helpful virtual receptionist",
            company_description="Professional business providing excellent customer service",
            company_services=["Customer Support", "General Inquiries"],
            max_transfer_attempts=3,
            default_department="customer_service",
            business_hours_start="09:00",
            business_hours_end="17:00",
            timezone="UTC",
            business_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
            enable_spam_detection=True,
            enable_call_recording=True,
            enable_transcription=True,
            enable_emotion_detection=False,
            enable_vip_handling=True,
            primary_language="auto",
            supported_languages=["en", "es"],
            welcome_message="Hello! Thank you for calling. I'm Sofia, your AI assistant. How may I help you today?",
            afterhours_message="Thank you for calling. We are currently closed. Please leave a message or call back during business hours.",
            transfer_rules=[],
            spam_keywords=["insurance", "warranty", "loan", "debt"],
            vip_phone_numbers=[]
        )
        
        session.add(settings)
    
    async def _create_default_departments(self, session, tenant_id: uuid.UUID):
        """Create default departments for new tenant."""
        departments = [
            Department(
                tenant_id=tenant_id,
                name="Customer Service",
                code="CS",
                description="General customer service and support",
                is_active=True,
                is_default=True,
                max_queue_size=10,
                queue_timeout=300,
                transfer_keywords=["help", "support", "service", "customer"],
                priority=1,
                routing_strategy="round_robin"
            ),
            Department(
                tenant_id=tenant_id,
                name="Sales",
                code="SALES",
                description="Sales and new customer inquiries",
                is_active=True,
                is_default=False,
                max_queue_size=5,
                queue_timeout=180,
                transfer_keywords=["sales", "buy", "purchase", "pricing", "quote"],
                priority=2,
                routing_strategy="skills_based"
            )
        ]
        
        for dept in departments:
            session.add(dept)
    
    async def _create_default_knowledge_base(self, session, tenant_id: uuid.UUID):
        """Create default knowledge base entries."""
        knowledge_entries = [
            KnowledgeBase(
                tenant_id=tenant_id,
                question="What are your business hours?",
                answer="Our business hours are Monday through Friday, 9:00 AM to 5:00 PM.",
                category="general",
                priority=1,
                confidence_threshold=0.8,
                is_active=True,
                is_approved=True,
                language="en",
                keywords=["hours", "open", "closed", "time", "schedule"]
            ),
            KnowledgeBase(
                tenant_id=tenant_id,
                question="How can I contact customer service?",
                answer="You can reach our customer service team by calling this number or I can transfer you directly.",
                category="general",
                priority=1,
                confidence_threshold=0.8,
                is_active=True,
                is_approved=True,
                language="en",
                keywords=["contact", "customer service", "support", "help"]
            )
        ]
        
        for entry in knowledge_entries:
            session.add(entry)
    
    async def _create_default_spam_rules(self, session, tenant_id: uuid.UUID):
        """Create default spam detection rules."""
        spam_rules = [
            SpamRule(
                tenant_id=tenant_id,
                name="Insurance Sales",
                description="Detect insurance sales calls",
                rule_type="keyword",
                pattern="insurance|health insurance|life insurance",
                is_regex=True,
                case_sensitive=False,
                weight=15,
                threshold=0.7,
                action="flag",
                is_active=True,
                is_global=False
            ),
            SpamRule(
                tenant_id=tenant_id,
                name="Warranty Calls",
                description="Detect warranty extension calls",
                rule_type="keyword",
                pattern="warranty|extended warranty|car warranty",
                is_regex=True,
                case_sensitive=False,
                weight=20,
                threshold=0.8,
                action="block",
                is_active=True,
                is_global=False
            )
        ]
        
        for rule in spam_rules:
            session.add(rule)
    
    async def _log_tenant_data_counts(self, session, tenant_id: uuid.UUID, stage: str):
        """Log data counts for audit purposes."""
        try:
            tables = [
                "departments", "agents", "calls", "knowledge_base", 
                "spam_rules", "call_analytics", "agent_metrics"
            ]
            
            counts = {}
            for table in tables:
                result = await session.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                counts[table] = result.scalar()
            
            self.logger.info(
                f"Tenant data counts - {stage}",
                tenant_id=str(tenant_id),
                counts=counts
            )
            
        except Exception as e:
            self.logger.warning("Failed to log tenant data counts", error=str(e))
    
    async def _verify_tenant_cleanup(self, session, tenant_id: uuid.UUID):
        """Verify that all tenant data has been cleaned up."""
        try:
            # Check main tenant record
            tenant_result = await session.execute(
                "SELECT COUNT(*) FROM tenants WHERE id = :tenant_id",
                {"tenant_id": tenant_id}
            )
            tenant_count = tenant_result.scalar()
            
            if tenant_count > 0:
                raise TenantServiceError("Tenant record was not deleted")
            
            # Check related tables (should be 0 due to CASCADE)
            tables_to_check = [
                "tenant_settings", "departments", "agents", "calls",
                "knowledge_base", "spam_rules", "call_analytics", "agent_metrics"
            ]
            
            for table in tables_to_check:
                result = await session.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                count = result.scalar()
                
                if count > 0:
                    self.logger.warning(
                        f"Cleanup incomplete: {count} records remain in {table}",
                        tenant_id=str(tenant_id),
                        table=table,
                        remaining_count=count
                    )
            
            self.logger.info("Tenant cleanup verification completed", tenant_id=str(tenant_id))
            
        except Exception as e:
            self.logger.error("Failed to verify tenant cleanup", tenant_id=str(tenant_id), error=str(e))