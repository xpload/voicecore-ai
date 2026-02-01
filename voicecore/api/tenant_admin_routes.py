"""
Tenant Admin API routes for VoiceCore AI.

Provides REST endpoints for tenant-specific configuration, AI training,
knowledge base management, and tenant analytics with proper tenant admin authentication.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Header
from pydantic import BaseModel, Field

from voicecore.services.tenant_admin_service import (
    TenantAdminService,
    TenantAnalytics,
    AITrainingData,
    KnowledgeBaseStats,
    TenantAdminServiceError,
    UnauthorizedTenantAdminError,
    TenantConfigurationError
)


router = APIRouter(prefix="/api/v1/tenant-admin", tags=["tenant-admin"])


# Request/Response Models
class TenantAdminAuth(BaseModel):
    """Tenant admin authentication model."""
    tenant_id: uuid.UUID = Field(..., description="Tenant UUID")
    user_id: str = Field(..., description="Tenant admin user ID")
    api_key: str = Field(..., description="Tenant admin API key")


class TenantAnalyticsResponse(BaseModel):
    """Response model for tenant analytics."""
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


class AITrainingDataResponse(BaseModel):
    """Response model for AI training data."""
    tenant_id: uuid.UUID
    training_mode: bool
    custom_responses: Dict[str, str]
    conversation_flows: List[Dict[str, Any]]
    knowledge_base_entries: int
    training_conversations: int
    accuracy_score: float
    last_training_date: Optional[datetime]
    pending_approvals: int


class UpdateAIConfigRequest(BaseModel):
    """Request model for updating AI configuration."""
    ai_name: Optional[str] = None
    ai_gender: Optional[str] = None
    ai_voice_id: Optional[str] = None
    ai_personality: Optional[str] = None
    welcome_message: Optional[str] = None
    afterhours_message: Optional[str] = None
    primary_language: Optional[str] = None
    supported_languages: Optional[List[str]] = None
    max_transfer_attempts: Optional[int] = None
    training_mode: Optional[bool] = None


class KnowledgeBaseStatsResponse(BaseModel):
    """Response model for knowledge base statistics."""
    total_entries: int
    active_entries: int
    pending_approval: int
    categories: List[Dict[str, int]]
    languages: List[Dict[str, int]]
    most_used_entries: List[Dict[str, Any]]
    accuracy_ratings: Dict[str, float]


class CreateKnowledgeBaseEntryRequest(BaseModel):
    """Request model for creating knowledge base entry."""
    question: str = Field(..., description="Question text")
    answer: str = Field(..., description="Answer text")
    category: Optional[str] = Field("general", description="Entry category")
    priority: Optional[int] = Field(1, description="Priority level")
    confidence_threshold: Optional[float] = Field(0.8, description="Confidence threshold")
    is_active: Optional[bool] = Field(True, description="Whether entry is active")
    is_approved: Optional[bool] = Field(False, description="Whether entry is approved")
    language: Optional[str] = Field("en", description="Language code")
    keywords: Optional[List[str]] = Field([], description="Keywords for matching")


class UpdateKnowledgeBaseEntryRequest(BaseModel):
    """Request model for updating knowledge base entry."""
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    confidence_threshold: Optional[float] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    language: Optional[str] = None
    keywords: Optional[List[str]] = None


class TenantConfigurationResponse(BaseModel):
    """Response model for tenant configuration."""
    tenant: Dict[str, Any]
    ai_settings: Dict[str, Any]
    departments: List[Dict[str, Any]]
    spam_rules: List[Dict[str, Any]]


class UpdateTenantConfigurationRequest(BaseModel):
    """Request model for updating tenant configuration."""
    tenant: Optional[Dict[str, Any]] = None
    ai_settings: Optional[Dict[str, Any]] = None


# Dependency injection
def get_tenant_admin_service() -> TenantAdminService:
    """Get tenant admin service instance."""
    return TenantAdminService()


async def verify_tenant_admin(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID"),
    x_tenant_admin_user_id: str = Header(..., description="Tenant admin user ID"),
    x_tenant_admin_api_key: str = Header(..., description="Tenant admin API key"),
    admin_service: TenantAdminService = Depends(get_tenant_admin_service)
) -> tuple[TenantAdminService, uuid.UUID]:
    """
    Verify tenant admin credentials and return admin service with tenant ID.
    
    Args:
        tenant_id: Tenant UUID from path
        x_tenant_admin_user_id: Tenant admin user ID from header
        x_tenant_admin_api_key: Tenant admin API key from header
        admin_service: Tenant admin service instance
        
    Returns:
        tuple[TenantAdminService, uuid.UUID]: Verified admin service and tenant ID
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        await admin_service.verify_tenant_admin_access(
            tenant_id, x_tenant_admin_user_id, x_tenant_admin_api_key
        )
        return admin_service, tenant_id
    except UnauthorizedTenantAdminError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication verification failed")


# API Endpoints
@router.get("/{tenant_id}/analytics", response_model=TenantAnalyticsResponse)
async def get_tenant_analytics(
    period_days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_service_and_tenant: tuple[TenantAdminService, uuid.UUID] = Depends(verify_tenant_admin)
):
    """
    Get comprehensive analytics for the tenant.
    
    Returns detailed analytics including call statistics, agent performance,
    AI resolution rates, and department performance for the specified period.
    """
    try:
        admin_service, tenant_id = admin_service_and_tenant
        
        analytics = await admin_service.get_tenant_analytics(
            tenant_id=tenant_id,
            period_days=period_days
        )
        
        return TenantAnalyticsResponse(**analytics.to_dict())
        
    except TenantAdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{tenant_id}/ai-training", response_model=AITrainingDataResponse)
async def get_ai_training_data(
    admin_service_and_tenant: tuple[TenantAdminService, uuid.UUID] = Depends(verify_tenant_admin)
):
    """
    Get AI training configuration and statistics.
    
    Returns AI training data including custom responses, conversation flows,
    training statistics, and pending approvals.
    """
    try:
        admin_service, tenant_id = admin_service_and_tenant
        
        training_data = await admin_service.get_ai_training_data(tenant_id)
        
        return AITrainingDataResponse(**training_data.to_dict())
        
    except TenantAdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{tenant_id}/ai-configuration")
async def update_ai_configuration(
    request: UpdateAIConfigRequest,
    admin_service_and_tenant: tuple[TenantAdminService, uuid.UUID] = Depends(verify_tenant_admin)
):
    """
    Update AI configuration for the tenant.
    
    Updates AI settings including personality, voice, messages, and training mode.
    Only specified fields will be updated, others remain unchanged.
    """
    try:
        admin_service, tenant_id = admin_service_and_tenant
        
        # Convert request to dict, excluding None values
        config_updates = {
            k: v for k, v in request.dict().items() 
            if v is not None
        }
        
        if not config_updates:
            raise HTTPException(status_code=400, detail="No configuration updates provided")
        
        success = await admin_service.update_ai_configuration(tenant_id, config_updates)
        
        if success:
            return {
                "status": "success",
                "message": "AI configuration updated successfully",
                "updated_fields": list(config_updates.keys())
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update AI configuration")
        
    except TenantConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{tenant_id}/knowledge-base/stats", response_model=KnowledgeBaseStatsResponse)
async def get_knowledge_base_stats(
    admin_service_and_tenant: tuple[TenantAdminService, uuid.UUID] = Depends(verify_tenant_admin)
):
    """
    Get knowledge base statistics for the tenant.
    
    Returns comprehensive statistics including entry counts, categories,
    languages, most used entries, and accuracy ratings.
    """
    try:
        admin_service, tenant_id = admin_service_and_tenant
        
        stats = await admin_service.get_knowledge_base_stats(tenant_id)
        
        return KnowledgeBaseStatsResponse(**stats.to_dict())
        
    except TenantAdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{tenant_id}/knowledge-base/entries")
async def create_knowledge_base_entry(
    request: CreateKnowledgeBaseEntryRequest,
    admin_service_and_tenant: tuple[TenantAdminService, uuid.UUID] = Depends(verify_tenant_admin)
):
    """
    Create a new knowledge base entry.
    
    Creates a new knowledge base entry with the specified question, answer,
    and configuration. Entry will be pending approval by default.
    """
    try:
        admin_service, tenant_id = admin_service_and_tenant
        
        entry_data = request.dict()
        
        created_entry = await admin_service.create_knowledge_base_entry(
            tenant_id, entry_data
        )
        
        return {
            "status": "success",
            "message": "Knowledge base entry created successfully",
            "entry": created_entry
        }
        
    except TenantAdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{tenant_id}/knowledge-base/entries/{entry_id}")
async def update_knowledge_base_entry(
    entry_id: uuid.UUID = Path(..., description="Knowledge base entry UUID"),
    request: UpdateKnowledgeBaseEntryRequest = ...,
    admin_service_and_tenant: tuple[TenantAdminService, uuid.UUID] = Depends(verify_tenant_admin)
):
    """
    Update a knowledge base entry.
    
    Updates the specified knowledge base entry with the provided data.
    Only specified fields will be updated, others remain unchanged.
    """
    try:
        admin_service, tenant_id = admin_service_and_tenant
        
        # Convert request to dict, excluding None values
        update_data = {
            k: v for k, v in request.dict().items() 
            if v is not None
        }
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        success = await admin_service.update_knowledge_base_entry(
            tenant_id, entry_id, update_data
        )
        
        if success:
            return {
                "status": "success",
                "message": "Knowledge base entry updated successfully",
                "updated_fields": list(update_data.keys())
            }
        else:
            raise HTTPException(status_code=404, detail="Knowledge base entry not found")
        
    except TenantAdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{tenant_id}/knowledge-base/entries/{entry_id}")
async def delete_knowledge_base_entry(
    entry_id: uuid.UUID = Path(..., description="Knowledge base entry UUID"),
    admin_service_and_tenant: tuple[TenantAdminService, uuid.UUID] = Depends(verify_tenant_admin)
):
    """
    Delete a knowledge base entry.
    
    Permanently deletes the specified knowledge base entry.
    This action cannot be undone.
    """
    try:
        admin_service, tenant_id = admin_service_and_tenant
        
        success = await admin_service.delete_knowledge_base_entry(tenant_id, entry_id)
        
        if success:
            return {
                "status": "success",
                "message": "Knowledge base entry deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Knowledge base entry not found")
        
    except TenantAdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{tenant_id}/configuration", response_model=TenantConfigurationResponse)
async def get_tenant_configuration(
    admin_service_and_tenant: tuple[TenantAdminService, uuid.UUID] = Depends(verify_tenant_admin)
):
    """
    Get comprehensive tenant configuration.
    
    Returns complete tenant configuration including basic info, AI settings,
    departments, and spam rules for administrative management.
    """
    try:
        admin_service, tenant_id = admin_service_and_tenant
        
        configuration = await admin_service.get_tenant_configuration(tenant_id)
        
        return TenantConfigurationResponse(**configuration)
        
    except TenantAdminServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{tenant_id}/configuration")
async def update_tenant_configuration(
    request: UpdateTenantConfigurationRequest,
    admin_service_and_tenant: tuple[TenantAdminService, uuid.UUID] = Depends(verify_tenant_admin)
):
    """
    Update tenant configuration.
    
    Updates tenant configuration including basic info and AI settings.
    Only specified sections and fields will be updated, others remain unchanged.
    """
    try:
        admin_service, tenant_id = admin_service_and_tenant
        
        # Convert request to dict, excluding None values
        config_updates = {
            k: v for k, v in request.dict().items() 
            if v is not None
        }
        
        if not config_updates:
            raise HTTPException(status_code=400, detail="No configuration updates provided")
        
        success = await admin_service.update_tenant_configuration(tenant_id, config_updates)
        
        if success:
            return {
                "status": "success",
                "message": "Tenant configuration updated successfully",
                "updated_sections": list(config_updates.keys())
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update tenant configuration")
        
    except TenantConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{tenant_id}/status")
async def get_tenant_admin_panel_status(
    tenant_id: uuid.UUID = Path(..., description="Tenant UUID")
):
    """
    Get tenant admin panel status (no authentication required).
    
    Returns basic status information about the tenant admin panel
    availability without requiring authentication.
    """
    return {
        "status": "operational",
        "service": "VoiceCore AI Tenant Admin Panel",
        "tenant_id": str(tenant_id),
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "authentication_required": True,
        "features": [
            "tenant_analytics",
            "ai_training",
            "knowledge_base_management",
            "configuration_management"
        ]
    }