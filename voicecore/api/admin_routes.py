"""
Super Admin API routes for VoiceCore AI.

Provides REST endpoints for global system configuration, tenant management,
and system-wide analytics and monitoring with proper super admin authentication.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Header
from pydantic import BaseModel, Field

from voicecore.services.admin_service import (
    AdminService,
    SystemMetrics,
    TenantSummary,
    SystemConfiguration,
    AdminServiceError,
    UnauthorizedAdminError,
    SystemConfigurationError
)


router = APIRouter(prefix="/api/v1/admin", tags=["super-admin"])


# Request/Response Models
class SuperAdminAuth(BaseModel):
    """Super admin authentication model."""
    user_id: str = Field(..., description="Super admin user ID")
    api_key: str = Field(..., description="Super admin API key")


class SystemMetricsResponse(BaseModel):
    """Response model for system metrics."""
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


class TenantSummaryResponse(BaseModel):
    """Response model for tenant summary."""
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


class CreateTenantRequest(BaseModel):
    """Request model for creating tenant as admin."""
    company_name: str = Field(..., description="Company name")
    admin_email: str = Field(..., description="Admin email address")
    phone_number: str = Field(..., description="Primary phone number")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Optional tenant configuration")


class TenantActionRequest(BaseModel):
    """Request model for tenant actions."""
    reason: Optional[str] = Field(None, description="Reason for action")


class SystemConfigurationResponse(BaseModel):
    """Response model for system configuration."""
    max_tenants: int
    max_agents_per_tenant: int
    default_call_timeout_seconds: int
    max_recording_duration_minutes: int
    auto_transcription_enabled: bool
    spam_detection_enabled: bool
    rate_limit_requests_per_minute: int
    maintenance_mode: bool
    debug_logging_enabled: bool


class UpdateConfigurationRequest(BaseModel):
    """Request model for updating system configuration."""
    max_tenants: Optional[int] = None
    max_agents_per_tenant: Optional[int] = None
    default_call_timeout_seconds: Optional[int] = None
    max_recording_duration_minutes: Optional[int] = None
    auto_transcription_enabled: Optional[bool] = None
    spam_detection_enabled: Optional[bool] = None
    rate_limit_requests_per_minute: Optional[int] = None
    maintenance_mode: Optional[bool] = None
    debug_logging_enabled: Optional[bool] = None


class SystemLogResponse(BaseModel):
    """Response model for system logs."""
    timestamp: str
    level: str
    service: str
    message: str
    correlation_id: str


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    overall_status: str
    timestamp: str
    components: Dict[str, Any]


# Dependency injection
def get_admin_service() -> AdminService:
    """Get admin service instance."""
    return AdminService()


async def verify_super_admin(
    x_admin_user_id: str = Header(..., description="Super admin user ID"),
    x_admin_api_key: str = Header(..., description="Super admin API key"),
    admin_service: AdminService = Depends(get_admin_service)
) -> AdminService:
    """
    Verify super admin credentials and return admin service.
    
    Args:
        x_admin_user_id: Super admin user ID from header
        x_admin_api_key: Super admin API key from header
        admin_service: Admin service instance
        
    Returns:
        AdminService: Verified admin service instance
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        await admin_service.verify_super_admin_access(x_admin_user_id, x_admin_api_key)
        return admin_service
    except UnauthorizedAdminError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication verification failed")


# API Endpoints
@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    admin_service: AdminService = Depends(verify_super_admin)
):
    """
    Get comprehensive system metrics.
    
    Returns system-wide metrics including tenant counts, call statistics,
    performance metrics, and resource usage for monitoring dashboards.
    """
    try:
        metrics = await admin_service.get_system_metrics()
        return SystemMetricsResponse(**metrics.to_dict())
        
    except AdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tenants", response_model=List[TenantSummaryResponse])
async def get_all_tenants(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tenants to return"),
    offset: int = Query(0, ge=0, description="Number of tenants to skip"),
    status: Optional[str] = Query(None, regex="^(active|inactive)$", description="Filter by status"),
    admin_service: AdminService = Depends(verify_super_admin)
):
    """
    Get summary information for all tenants.
    
    Returns paginated list of tenant summaries with key metrics
    including agent counts, call volumes, and usage statistics.
    """
    try:
        tenant_summaries = await admin_service.get_all_tenants_summary(
            limit=limit,
            offset=offset,
            status_filter=status
        )
        
        return [
            TenantSummaryResponse(**summary.to_dict())
            for summary in tenant_summaries
        ]
        
    except AdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tenants")
async def create_tenant_as_admin(
    request: CreateTenantRequest,
    admin_service: AdminService = Depends(verify_super_admin)
):
    """
    Create a new tenant as super admin.
    
    Creates a new tenant with the specified configuration and
    returns the tenant information including credentials.
    """
    try:
        tenant_data = await admin_service.create_tenant_as_admin(
            company_name=request.company_name,
            admin_email=request.admin_email,
            phone_number=request.phone_number,
            configuration=request.configuration
        )
        
        return {
            "status": "success",
            "message": "Tenant created successfully",
            "tenant_data": tenant_data
        }
        
    except AdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID"),
    request: TenantActionRequest = ...,
    admin_service: AdminService = Depends(verify_super_admin)
):
    """
    Suspend a tenant (admin action).
    
    Suspends the specified tenant and deactivates all associated agents.
    This action can be reversed using the reactivate endpoint.
    """
    try:
        success = await admin_service.suspend_tenant(
            tenant_id=tenant_id,
            reason=request.reason or "Suspended by super admin"
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Tenant {tenant_id} suspended successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to suspend tenant")
        
    except AdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tenants/{tenant_id}/reactivate")
async def reactivate_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID"),
    admin_service: AdminService = Depends(verify_super_admin)
):
    """
    Reactivate a suspended tenant.
    
    Reactivates the specified tenant, allowing normal operations to resume.
    Agents will need to be manually reactivated if needed.
    """
    try:
        success = await admin_service.reactivate_tenant(tenant_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Tenant {tenant_id} reactivated successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to reactivate tenant")
        
    except AdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/configuration", response_model=SystemConfigurationResponse)
async def get_system_configuration(
    admin_service: AdminService = Depends(verify_super_admin)
):
    """
    Get current system configuration.
    
    Returns the current global system configuration including
    limits, feature flags, and operational parameters.
    """
    try:
        config = await admin_service.get_system_configuration()
        return SystemConfigurationResponse(**config.to_dict())
        
    except SystemConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/configuration", response_model=SystemConfigurationResponse)
async def update_system_configuration(
    request: UpdateConfigurationRequest,
    admin_service: AdminService = Depends(verify_super_admin)
):
    """
    Update system configuration.
    
    Updates the global system configuration with the provided values.
    Only specified fields will be updated, others remain unchanged.
    """
    try:
        # Convert request to dict, excluding None values
        config_updates = {
            k: v for k, v in request.dict().items() 
            if v is not None
        }
        
        if not config_updates:
            raise HTTPException(status_code=400, detail="No configuration updates provided")
        
        updated_config = await admin_service.update_system_configuration(config_updates)
        return SystemConfigurationResponse(**updated_config.to_dict())
        
    except SystemConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/logs", response_model=List[SystemLogResponse])
async def get_system_logs(
    level: str = Query("INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$", description="Log level filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    admin_service: AdminService = Depends(verify_super_admin)
):
    """
    Get system logs for monitoring.
    
    Returns system logs filtered by level and time range for
    monitoring and debugging purposes.
    """
    try:
        logs = await admin_service.get_system_logs(
            level=level,
            limit=limit,
            start_time=start_time,
            end_time=end_time
        )
        
        return [SystemLogResponse(**log) for log in logs]
        
    except AdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health", response_model=HealthCheckResponse)
async def perform_system_health_check(
    admin_service: AdminService = Depends(verify_super_admin)
):
    """
    Perform comprehensive system health check.
    
    Returns detailed health status for all system components
    including database, external services, and system resources.
    """
    try:
        health_status = await admin_service.perform_system_health_check()
        return HealthCheckResponse(**health_status)
        
    except Exception as e:
        # Health check should not fail completely
        return HealthCheckResponse(
            overall_status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            components={"error": str(e)}
        )


@router.get("/status")
async def get_admin_panel_status():
    """
    Get admin panel status (no authentication required).
    
    Returns basic status information about the admin panel
    availability without requiring authentication.
    """
    return {
        "status": "operational",
        "service": "VoiceCore AI Super Admin Panel",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "authentication_required": True
    }