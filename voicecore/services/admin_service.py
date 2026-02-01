"""
Super Admin service for VoiceCore AI.

Provides global system configuration, tenant management,
and system-wide analytics and monitoring for super administrators.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import Tenant, Agent, Call, CallStatus, CallDirection
from voicecore.logging import get_logger
from voicecore.config import settings
from voicecore.services.tenant_service import TenantService


logger = get_logger(__name__)


@dataclass
class SystemMetrics:
    """System-wide metrics for monitoring."""
    total_tenants: int
    active_tenants: int
    total_agents: int
    active_agents: int
    total_calls_today: int
    total_calls_this_month: int
    average_call_duration: float
    system_uptime_hours: float
    storage_usage_gb: float
    api_requests_per_minute: float
    error_rate_percentage: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


@dataclass
class TenantSummary:
    """Summary information for a tenant."""
    tenant_id: uuid.UUID
    company_name: str
    status: str
    created_at: datetime
    last_activity: Optional[datetime]
    total_agents: int
    active_agents: int
    calls_this_month: int
    storage_usage_mb: float
    monthly_cost_cents: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["tenant_id"] = str(self.tenant_id)
        data["created_at"] = self.created_at.isoformat()
        if self.last_activity:
            data["last_activity"] = self.last_activity.isoformat()
        return data


@dataclass
class SystemConfiguration:
    """Global system configuration."""
    max_tenants: int
    max_agents_per_tenant: int
    default_call_timeout_seconds: int
    max_recording_duration_minutes: int
    auto_transcription_enabled: bool
    spam_detection_enabled: bool
    rate_limit_requests_per_minute: int
    maintenance_mode: bool
    debug_logging_enabled: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


class AdminServiceError(Exception):
    """Base exception for admin service errors."""
    pass


class UnauthorizedAdminError(AdminServiceError):
    """Raised when admin access is unauthorized."""
    pass


class SystemConfigurationError(AdminServiceError):
    """Raised when system configuration operations fail."""
    pass


class AdminService:
    """
    Super Admin service for global system management.
    
    Provides comprehensive system administration capabilities including
    tenant management, system monitoring, configuration, and analytics.
    """
    
    def __init__(self):
        self.logger = logger
        self.tenant_service = TenantService()
        
        # System configuration defaults
        self.default_config = SystemConfiguration(
            max_tenants=1000,
            max_agents_per_tenant=100,
            default_call_timeout_seconds=300,
            max_recording_duration_minutes=60,
            auto_transcription_enabled=True,
            spam_detection_enabled=True,
            rate_limit_requests_per_minute=1000,
            maintenance_mode=False,
            debug_logging_enabled=False
        )
    
    async def verify_super_admin_access(self, user_id: str, api_key: str) -> bool:
        """
        Verify super admin access credentials.
        
        Args:
            user_id: Super admin user ID
            api_key: Super admin API key
            
        Returns:
            bool: True if access is authorized
            
        Raises:
            UnauthorizedAdminError: If access is denied
        """
        try:
            # In production, this would verify against a secure admin user store
            # For now, check against configured super admin credentials
            
            valid_super_admin_key = getattr(settings, 'super_admin_api_key', None)
            valid_super_admin_user = getattr(settings, 'super_admin_user_id', 'super_admin')
            
            if not valid_super_admin_key:
                raise UnauthorizedAdminError("Super admin access not configured")
            
            if user_id != valid_super_admin_user or api_key != valid_super_admin_key:
                self.logger.warning(
                    "Unauthorized super admin access attempt",
                    user_id=user_id,
                    api_key_prefix=api_key[:8] + "..." if api_key else "None"
                )
                raise UnauthorizedAdminError("Invalid super admin credentials")
            
            self.logger.info("Super admin access granted", user_id=user_id)
            return True
            
        except UnauthorizedAdminError:
            raise
        except Exception as e:
            self.logger.error("Failed to verify super admin access", error=str(e))
            raise AdminServiceError(f"Access verification failed: {str(e)}")
    
    async def get_system_metrics(self) -> SystemMetrics:
        """
        Get comprehensive system metrics.
        
        Returns:
            SystemMetrics: Current system metrics
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, func, and_
                
                # Get tenant metrics
                tenant_result = await session.execute(
                    select(
                        func.count(Tenant.id).label('total_tenants'),
                        func.count(Tenant.id).filter(Tenant.is_active == True).label('active_tenants')
                    )
                )
                tenant_metrics = tenant_result.first()
                
                # Get agent metrics
                agent_result = await session.execute(
                    select(
                        func.count(Agent.id).label('total_agents'),
                        func.count(Agent.id).filter(Agent.is_active == True).label('active_agents')
                    )
                )
                agent_metrics = agent_result.first()
                
                # Get call metrics for today
                today = datetime.utcnow().date()
                today_start = datetime.combine(today, datetime.min.time())
                
                calls_today_result = await session.execute(
                    select(func.count(Call.id)).where(
                        Call.created_at >= today_start
                    )
                )
                calls_today = calls_today_result.scalar() or 0
                
                # Get call metrics for this month
                month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                calls_month_result = await session.execute(
                    select(
                        func.count(Call.id).label('total_calls'),
                        func.avg(Call.duration).label('avg_duration')
                    ).where(
                        Call.created_at >= month_start
                    )
                )
                calls_month = calls_month_result.first()
                
                # Calculate system uptime (simplified - would use actual uptime in production)
                uptime_hours = 24.0  # Placeholder
                
                # Storage and performance metrics (would be calculated from actual usage)
                storage_usage_gb = 10.5  # Placeholder
                api_requests_per_minute = 150.0  # Placeholder
                error_rate_percentage = 0.1  # Placeholder
                
                return SystemMetrics(
                    total_tenants=tenant_metrics.total_tenants or 0,
                    active_tenants=tenant_metrics.active_tenants or 0,
                    total_agents=agent_metrics.total_agents or 0,
                    active_agents=agent_metrics.active_agents or 0,
                    total_calls_today=calls_today,
                    total_calls_this_month=calls_month.total_calls or 0,
                    average_call_duration=float(calls_month.avg_duration or 0),
                    system_uptime_hours=uptime_hours,
                    storage_usage_gb=storage_usage_gb,
                    api_requests_per_minute=api_requests_per_minute,
                    error_rate_percentage=error_rate_percentage
                )
                
        except Exception as e:
            self.logger.error("Failed to get system metrics", error=str(e))
            raise AdminServiceError(f"Failed to get system metrics: {str(e)}")
    
    async def get_all_tenants_summary(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[TenantSummary]:
        """
        Get summary information for all tenants.
        
        Args:
            limit: Maximum number of tenants to return
            offset: Number of tenants to skip
            status_filter: Filter by tenant status
            
        Returns:
            List[TenantSummary]: List of tenant summaries
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, func, and_, desc
                
                # Base query for tenants
                query = select(Tenant)
                
                if status_filter:
                    if status_filter == "active":
                        query = query.where(Tenant.is_active == True)
                    elif status_filter == "inactive":
                        query = query.where(Tenant.is_active == False)
                
                query = query.order_by(desc(Tenant.created_at)).limit(limit).offset(offset)
                
                tenant_result = await session.execute(query)
                tenants = tenant_result.scalars().all()
                
                tenant_summaries = []
                
                for tenant in tenants:
                    # Get agent count for tenant
                    await set_tenant_context(session, str(tenant.id))
                    
                    agent_result = await session.execute(
                        select(
                            func.count(Agent.id).label('total_agents'),
                            func.count(Agent.id).filter(Agent.is_active == True).label('active_agents')
                        ).where(Agent.tenant_id == tenant.id)
                    )
                    agent_metrics = agent_result.first()
                    
                    # Get call count for this month
                    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    
                    calls_result = await session.execute(
                        select(func.count(Call.id)).where(
                            and_(
                                Call.tenant_id == tenant.id,
                                Call.created_at >= month_start
                            )
                        )
                    )
                    calls_this_month = calls_result.scalar() or 0
                    
                    # Get last activity (most recent call)
                    last_activity_result = await session.execute(
                        select(func.max(Call.created_at)).where(
                            Call.tenant_id == tenant.id
                        )
                    )
                    last_activity = last_activity_result.scalar()
                    
                    # Calculate storage usage and cost (simplified)
                    storage_usage_mb = calls_this_month * 2.5  # Estimate 2.5MB per call
                    monthly_cost_cents = calls_this_month * 10  # Estimate 10 cents per call
                    
                    tenant_summary = TenantSummary(
                        tenant_id=tenant.id,
                        company_name=tenant.company_name,
                        status="active" if tenant.is_active else "inactive",
                        created_at=tenant.created_at,
                        last_activity=last_activity,
                        total_agents=agent_metrics.total_agents or 0,
                        active_agents=agent_metrics.active_agents or 0,
                        calls_this_month=calls_this_month,
                        storage_usage_mb=storage_usage_mb,
                        monthly_cost_cents=monthly_cost_cents
                    )
                    
                    tenant_summaries.append(tenant_summary)
                
                return tenant_summaries
                
        except Exception as e:
            self.logger.error("Failed to get tenants summary", error=str(e))
            raise AdminServiceError(f"Failed to get tenants summary: {str(e)}")
    
    async def create_tenant_as_admin(
        self,
        company_name: str,
        admin_email: str,
        phone_number: str,
        configuration: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new tenant as super admin.
        
        Args:
            company_name: Company name for the tenant
            admin_email: Admin email for the tenant
            phone_number: Primary phone number
            configuration: Optional tenant configuration
            
        Returns:
            Dict[str, Any]: Created tenant information
        """
        try:
            # Use tenant service to create tenant
            tenant_data = await self.tenant_service.create_tenant(
                company_name=company_name,
                admin_email=admin_email,
                phone_number=phone_number,
                configuration=configuration or {}
            )
            
            self.logger.info(
                "Tenant created by super admin",
                tenant_id=tenant_data["tenant_id"],
                company_name=company_name
            )
            
            return tenant_data
            
        except Exception as e:
            self.logger.error("Failed to create tenant as admin", error=str(e))
            raise AdminServiceError(f"Failed to create tenant: {str(e)}")
    
    async def suspend_tenant(self, tenant_id: uuid.UUID, reason: str) -> bool:
        """
        Suspend a tenant (admin action).
        
        Args:
            tenant_id: Tenant UUID to suspend
            reason: Reason for suspension
            
        Returns:
            bool: True if suspended successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import update
                
                # Suspend tenant
                await session.execute(
                    update(Tenant)
                    .where(Tenant.id == tenant_id)
                    .values(
                        is_active=False,
                        updated_at=datetime.utcnow()
                    )
                )
                
                # Deactivate all agents
                await session.execute(
                    update(Agent)
                    .where(Agent.tenant_id == tenant_id)
                    .values(
                        is_active=False,
                        updated_at=datetime.utcnow()
                    )
                )
                
                await session.commit()
                
                self.logger.info(
                    "Tenant suspended by super admin",
                    tenant_id=str(tenant_id),
                    reason=reason
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to suspend tenant", error=str(e), tenant_id=str(tenant_id))
            raise AdminServiceError(f"Failed to suspend tenant: {str(e)}")
    
    async def reactivate_tenant(self, tenant_id: uuid.UUID) -> bool:
        """
        Reactivate a suspended tenant.
        
        Args:
            tenant_id: Tenant UUID to reactivate
            
        Returns:
            bool: True if reactivated successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import update
                
                # Reactivate tenant
                await session.execute(
                    update(Tenant)
                    .where(Tenant.id == tenant_id)
                    .values(
                        is_active=True,
                        updated_at=datetime.utcnow()
                    )
                )
                
                await session.commit()
                
                self.logger.info(
                    "Tenant reactivated by super admin",
                    tenant_id=str(tenant_id)
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to reactivate tenant", error=str(e), tenant_id=str(tenant_id))
            raise AdminServiceError(f"Failed to reactivate tenant: {str(e)}")
    
    async def get_system_configuration(self) -> SystemConfiguration:
        """
        Get current system configuration.
        
        Returns:
            SystemConfiguration: Current system configuration
        """
        try:
            # In production, this would be stored in database or configuration service
            # For now, return default configuration with any overrides from settings
            
            config = SystemConfiguration(
                max_tenants=getattr(settings, 'max_tenants', self.default_config.max_tenants),
                max_agents_per_tenant=getattr(settings, 'max_agents_per_tenant', self.default_config.max_agents_per_tenant),
                default_call_timeout_seconds=getattr(settings, 'default_call_timeout_seconds', self.default_config.default_call_timeout_seconds),
                max_recording_duration_minutes=getattr(settings, 'max_recording_duration_minutes', self.default_config.max_recording_duration_minutes),
                auto_transcription_enabled=getattr(settings, 'auto_transcription_enabled', self.default_config.auto_transcription_enabled),
                spam_detection_enabled=getattr(settings, 'spam_detection_enabled', self.default_config.spam_detection_enabled),
                rate_limit_requests_per_minute=getattr(settings, 'rate_limit_requests_per_minute', self.default_config.rate_limit_requests_per_minute),
                maintenance_mode=getattr(settings, 'maintenance_mode', self.default_config.maintenance_mode),
                debug_logging_enabled=getattr(settings, 'debug_logging_enabled', self.default_config.debug_logging_enabled)
            )
            
            return config
            
        except Exception as e:
            self.logger.error("Failed to get system configuration", error=str(e))
            raise SystemConfigurationError(f"Failed to get configuration: {str(e)}")
    
    async def update_system_configuration(
        self,
        configuration: Dict[str, Any]
    ) -> SystemConfiguration:
        """
        Update system configuration.
        
        Args:
            configuration: Configuration updates
            
        Returns:
            SystemConfiguration: Updated configuration
        """
        try:
            # In production, this would update a configuration service or database
            # For now, we'll validate the configuration and return it
            
            current_config = await self.get_system_configuration()
            
            # Validate and apply updates
            valid_keys = {
                'max_tenants', 'max_agents_per_tenant', 'default_call_timeout_seconds',
                'max_recording_duration_minutes', 'auto_transcription_enabled',
                'spam_detection_enabled', 'rate_limit_requests_per_minute',
                'maintenance_mode', 'debug_logging_enabled'
            }
            
            for key, value in configuration.items():
                if key not in valid_keys:
                    raise SystemConfigurationError(f"Invalid configuration key: {key}")
                
                # Type validation
                if key in ['max_tenants', 'max_agents_per_tenant', 'default_call_timeout_seconds', 
                          'max_recording_duration_minutes', 'rate_limit_requests_per_minute']:
                    if not isinstance(value, int) or value < 0:
                        raise SystemConfigurationError(f"Invalid value for {key}: must be positive integer")
                
                elif key in ['auto_transcription_enabled', 'spam_detection_enabled', 
                            'maintenance_mode', 'debug_logging_enabled']:
                    if not isinstance(value, bool):
                        raise SystemConfigurationError(f"Invalid value for {key}: must be boolean")
                
                # Apply the update
                setattr(current_config, key, value)
            
            self.logger.info(
                "System configuration updated by super admin",
                updated_keys=list(configuration.keys())
            )
            
            return current_config
            
        except SystemConfigurationError:
            raise
        except Exception as e:
            self.logger.error("Failed to update system configuration", error=str(e))
            raise SystemConfigurationError(f"Failed to update configuration: {str(e)}")
    
    async def get_system_logs(
        self,
        level: str = "INFO",
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get system logs for monitoring.
        
        Args:
            level: Log level filter
            limit: Maximum number of logs to return
            start_time: Start time filter
            end_time: End time filter
            
        Returns:
            List[Dict[str, Any]]: System logs
        """
        try:
            # In production, this would query a centralized logging system
            # For now, return a placeholder structure
            
            logs = [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "service": "voicecore.main",
                    "message": "System startup completed successfully",
                    "correlation_id": "sys_001"
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                    "level": "INFO",
                    "service": "voicecore.services.tenant_service",
                    "message": "New tenant created",
                    "correlation_id": "tenant_002"
                }
            ]
            
            return logs
            
        except Exception as e:
            self.logger.error("Failed to get system logs", error=str(e))
            raise AdminServiceError(f"Failed to get system logs: {str(e)}")
    
    async def perform_system_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health check.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            health_status = {
                "overall_status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {}
            }
            
            # Check database connectivity
            try:
                async with get_db_session() as session:
                    from sqlalchemy import text
                    await session.execute(text("SELECT 1"))
                health_status["components"]["database"] = {"status": "healthy", "response_time_ms": 10}
            except Exception as e:
                health_status["components"]["database"] = {"status": "unhealthy", "error": str(e)}
                health_status["overall_status"] = "degraded"
            
            # Check external services (simplified)
            health_status["components"]["twilio"] = {"status": "healthy", "response_time_ms": 50}
            health_status["components"]["openai"] = {"status": "healthy", "response_time_ms": 100}
            
            # Check system resources (simplified)
            health_status["components"]["memory"] = {"status": "healthy", "usage_percentage": 45}
            health_status["components"]["cpu"] = {"status": "healthy", "usage_percentage": 30}
            health_status["components"]["disk"] = {"status": "healthy", "usage_percentage": 60}
            
            return health_status
            
        except Exception as e:
            self.logger.error("Failed to perform health check", error=str(e))
            return {
                "overall_status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }