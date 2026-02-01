"""
Tenant management API routes for VoiceCore AI.

Provides REST API endpoints for tenant lifecycle management
with proper authentication and authorization.
"""

import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime

from voicecore.services.tenant_service import (
    TenantService, 
    TenantServiceError, 
    TenantNotFoundError, 
    TenantAlreadyExistsError
)
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/tenants", tags=["Tenants"])


# Pydantic models for request/response validation

class TenantCreateRequest(BaseModel):
    """Request model for creating a new tenant."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    subdomain: Optional[str] = Field(None, min_length=3, max_length=20, description="Subdomain for tenant access")
    domain: Optional[str] = Field(None, max_length=255, description="Custom domain")
    contact_email: EmailStr = Field(..., description="Primary contact email")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Primary contact phone")
    plan_type: str = Field(default="basic", description="Subscription plan type")
    monthly_credit_limit: int = Field(default=1000, ge=100, le=100000, description="Monthly call minutes limit")
    twilio_phone_number: Optional[str] = Field(None, description="Dedicated Twilio phone number")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional tenant settings")
    
    @validator("subdomain")
    def validate_subdomain(cls, v):
        if v is not None:
            if not v.isalnum():
                raise ValueError("Subdomain must contain only alphanumeric characters")
            if v.lower() in ["www", "api", "admin", "app", "mail", "ftp"]:
                raise ValueError("Subdomain is reserved")
        return v.lower() if v else None
    
    @validator("plan_type")
    def validate_plan_type(cls, v):
        valid_plans = ["basic", "professional", "enterprise"]
        if v not in valid_plans:
            raise ValueError(f"Plan type must be one of: {valid_plans}")
        return v
    
    @validator("twilio_phone_number")
    def validate_phone_number(cls, v):
        if v is not None and not v.startswith("+"):
            raise ValueError("Phone number must start with +")
        return v


class TenantUpdateRequest(BaseModel):
    """Request model for updating tenant information."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    plan_type: Optional[str] = None
    monthly_credit_limit: Optional[int] = Field(None, ge=100, le=100000)
    is_active: Optional[bool] = None
    twilio_phone_number: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    
    @validator("plan_type")
    def validate_plan_type(cls, v):
        if v is not None:
            valid_plans = ["basic", "professional", "enterprise"]
            if v not in valid_plans:
                raise ValueError(f"Plan type must be one of: {valid_plans}")
        return v


class TenantResponse(BaseModel):
    """Response model for tenant information."""
    
    id: uuid.UUID
    name: str
    subdomain: Optional[str]
    domain: Optional[str]
    is_active: bool
    plan_type: str
    contact_email: str
    contact_phone: Optional[str]
    monthly_credit_limit: int
    current_usage: int
    twilio_phone_number: Optional[str]
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    """Response model for tenant list."""
    
    tenants: List[TenantResponse]
    total: int
    skip: int
    limit: int


class TenantUsageStatsResponse(BaseModel):
    """Response model for tenant usage statistics."""
    
    total_agents: int
    active_agents: int
    total_departments: int
    calls_last_30_days: int
    knowledge_base_entries: int
    current_usage: int
    monthly_credit_limit: int
    usage_percentage: float


class TenantSettingsUpdateRequest(BaseModel):
    """Request model for updating tenant settings."""
    
    ai_name: Optional[str] = Field(None, min_length=1, max_length=100)
    ai_gender: Optional[str] = Field(None, regex="^(male|female)$")
    ai_voice_id: Optional[str] = None
    ai_personality: Optional[str] = None
    company_description: Optional[str] = None
    company_services: Optional[List[str]] = None
    max_transfer_attempts: Optional[int] = Field(None, ge=1, le=10)
    default_department: Optional[str] = None
    business_hours_start: Optional[str] = Field(None, regex="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    business_hours_end: Optional[str] = Field(None, regex="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: Optional[str] = None
    business_days: Optional[List[str]] = None
    enable_spam_detection: Optional[bool] = None
    enable_call_recording: Optional[bool] = None
    enable_transcription: Optional[bool] = None
    enable_emotion_detection: Optional[bool] = None
    enable_vip_handling: Optional[bool] = None
    primary_language: Optional[str] = None
    supported_languages: Optional[List[str]] = None
    welcome_message: Optional[str] = None
    afterhours_message: Optional[str] = None
    voicemail_message: Optional[str] = None
    transfer_rules: Optional[List[Dict[str, Any]]] = None
    spam_keywords: Optional[List[str]] = None
    vip_phone_numbers: Optional[List[str]] = None


# Dependency for getting tenant service
def get_tenant_service() -> TenantService:
    """Dependency to get tenant service instance."""
    return TenantService()


# API Routes

@router.post("/", response_model=TenantResponse, status_code=201)
async def create_tenant(
    tenant_data: TenantCreateRequest,
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    Create a new tenant with complete provisioning.
    
    Creates a new tenant with default departments, settings, and configuration.
    This endpoint is typically used by super administrators.
    """
    try:
        tenant = await tenant_service.create_tenant(tenant_data.dict())
        
        logger.info(
            "Tenant created via API",
            tenant_id=str(tenant.id),
            tenant_name=tenant.name
        )
        
        return TenantResponse.from_orm(tenant)
        
    except TenantAlreadyExistsError as e:
        logger.warning("Tenant creation failed - already exists", error=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except TenantServiceError as e:
        logger.error("Tenant creation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error creating tenant", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    active_only: bool = Query(False, description="Return only active tenants"),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    List tenants with pagination and filtering.
    
    Returns a paginated list of tenants. This endpoint is typically
    used by super administrators for tenant management.
    """
    try:
        tenants = await tenant_service.list_tenants(
            skip=skip, 
            limit=limit, 
            active_only=active_only
        )
        
        # For now, we'll use the length of returned tenants as total
        # In a real implementation, you'd want a separate count query
        total = len(tenants)
        
        return TenantListResponse(
            tenants=[TenantResponse.from_orm(tenant) for tenant in tenants],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error("Failed to list tenants", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID"),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    Get tenant information by ID.
    
    Returns detailed information about a specific tenant.
    """
    try:
        tenant = await tenant_service.get_tenant(tenant_id)
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        return TenantResponse.from_orm(tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get tenant", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/subdomain/{subdomain}", response_model=TenantResponse)
async def get_tenant_by_subdomain(
    subdomain: str = Path(..., description="Tenant subdomain"),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    Get tenant information by subdomain.
    
    Returns detailed information about a tenant identified by subdomain.
    """
    try:
        tenant = await tenant_service.get_tenant_by_subdomain(subdomain)
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        return TenantResponse.from_orm(tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get tenant by subdomain", subdomain=subdomain, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID"),
    update_data: TenantUpdateRequest = Body(...),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    Update tenant information.
    
    Updates the specified tenant with the provided data.
    Only non-null fields in the request will be updated.
    """
    try:
        # Filter out None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        tenant = await tenant_service.update_tenant(tenant_id, update_dict)
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        logger.info(
            "Tenant updated via API",
            tenant_id=str(tenant_id),
            updated_fields=list(update_dict.keys())
        )
        
        return TenantResponse.from_orm(tenant)
        
    except HTTPException:
        raise
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    except TenantServiceError as e:
        logger.error("Tenant update failed", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error updating tenant", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID"),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    Delete tenant and all associated data.
    
    **WARNING**: This operation permanently deletes the tenant and ALL
    associated data including agents, calls, analytics, etc.
    This action cannot be undone.
    """
    try:
        success = await tenant_service.delete_tenant(tenant_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        logger.info("Tenant deleted via API", tenant_id=str(tenant_id))
        
        return JSONResponse(status_code=204, content=None)
        
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    except TenantServiceError as e:
        logger.error("Tenant deletion failed", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error deleting tenant", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{tenant_id}/usage", response_model=TenantUsageStatsResponse)
async def get_tenant_usage_stats(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID"),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    Get tenant usage statistics.
    
    Returns comprehensive usage statistics for the specified tenant
    including agent counts, call volumes, and resource utilization.
    """
    try:
        stats = await tenant_service.get_tenant_usage_stats(tenant_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        return TenantUsageStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get tenant usage stats", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{tenant_id}/settings")
async def get_tenant_settings(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID"),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    Get tenant-specific settings.
    
    Returns the detailed configuration settings for the specified tenant
    including AI configuration, business rules, and feature flags.
    """
    try:
        settings = await tenant_service.get_tenant_settings(tenant_id)
        
        if not settings:
            raise HTTPException(status_code=404, detail="Tenant settings not found")
        
        # Convert to dict for response (excluding sensitive fields if any)
        settings_dict = {
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
            "enable_spam_detection": settings.enable_spam_detection,
            "enable_call_recording": settings.enable_call_recording,
            "enable_transcription": settings.enable_transcription,
            "enable_emotion_detection": settings.enable_emotion_detection,
            "enable_vip_handling": settings.enable_vip_handling,
            "primary_language": settings.primary_language,
            "supported_languages": settings.supported_languages,
            "welcome_message": settings.welcome_message,
            "afterhours_message": settings.afterhours_message,
            "voicemail_message": settings.voicemail_message,
            "transfer_rules": settings.transfer_rules,
            "spam_keywords": settings.spam_keywords,
            "vip_phone_numbers": settings.vip_phone_numbers
        }
        
        return settings_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get tenant settings", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{tenant_id}/settings")
async def update_tenant_settings(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID"),
    settings_data: TenantSettingsUpdateRequest = Body(...),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    Update tenant-specific settings.
    
    Updates the configuration settings for the specified tenant.
    Only non-null fields in the request will be updated.
    """
    try:
        # Filter out None values
        update_dict = {k: v for k, v in settings_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        settings = await tenant_service.update_tenant_settings(tenant_id, update_dict)
        
        if not settings:
            raise HTTPException(status_code=404, detail="Tenant settings not found")
        
        logger.info(
            "Tenant settings updated via API",
            tenant_id=str(tenant_id),
            updated_fields=list(update_dict.keys())
        )
        
        return {"message": "Settings updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update tenant settings", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")