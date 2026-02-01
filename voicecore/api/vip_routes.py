"""
VIP caller management API routes for VoiceCore AI.

Provides REST API endpoints for managing VIP callers, priority routing,
and special handling rules in the multitenant system.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from voicecore.services.vip_service import VIPService, VIPServiceError, VIPNotFoundError
from voicecore.models import VIPPriority, VIPStatus, VIPHandlingRule
from voicecore.middleware import get_current_tenant_id
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/vip", tags=["VIP Management"])


# Pydantic models for request/response
class VIPCallerCreate(BaseModel):
    """Request model for creating VIP caller."""
    phone_number: str = Field(..., description="Primary phone number")
    caller_name: str = Field(..., min_length=1, max_length=255, description="Caller name")
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    vip_level: VIPPriority = Field(VIPPriority.STANDARD, description="VIP priority level")
    status: VIPStatus = Field(VIPStatus.ACTIVE, description="VIP status")
    preferred_agent_id: Optional[uuid.UUID] = Field(None, description="Preferred agent UUID")
    preferred_department_id: Optional[uuid.UUID] = Field(None, description="Preferred department UUID")
    handling_rules: List[VIPHandlingRule] = Field(default_factory=list, description="Special handling rules")
    custom_greeting: Optional[str] = Field(None, description="Custom greeting message")
    custom_hold_music: Optional[str] = Field(None, description="Custom hold music URL")
    max_wait_time: int = Field(60, ge=10, le=600, description="Maximum wait time in seconds")
    callback_priority: int = Field(1, ge=1, le=10, description="Callback priority")
    email: Optional[str] = Field(None, description="Email address")
    alternative_phone: Optional[str] = Field(None, description="Alternative phone number")
    account_number: Optional[str] = Field(None, max_length=100, description="Account number")
    account_value: Optional[float] = Field(None, ge=0, description="Account value")
    valid_from: Optional[datetime] = Field(None, description="Valid from date")
    valid_until: Optional[datetime] = Field(None, description="Valid until date")
    notes: Optional[str] = Field(None, description="Internal notes")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('valid_until')
    def validate_dates(cls, v, values):
        if v and 'valid_from' in values and values['valid_from']:
            if v <= values['valid_from']:
                raise ValueError('valid_until must be after valid_from')
        return v


class VIPCallerUpdate(BaseModel):
    """Request model for updating VIP caller."""
    caller_name: Optional[str] = Field(None, min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    vip_level: Optional[VIPPriority] = None
    status: Optional[VIPStatus] = None
    preferred_agent_id: Optional[uuid.UUID] = None
    preferred_department_id: Optional[uuid.UUID] = None
    handling_rules: Optional[List[VIPHandlingRule]] = None
    custom_greeting: Optional[str] = None
    custom_hold_music: Optional[str] = None
    max_wait_time: Optional[int] = Field(None, ge=10, le=600)
    callback_priority: Optional[int] = Field(None, ge=1, le=10)
    email: Optional[str] = None
    alternative_phone: Optional[str] = None
    account_number: Optional[str] = Field(None, max_length=100)
    account_value: Optional[float] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class VIPCallerResponse(BaseModel):
    """Response model for VIP caller."""
    id: uuid.UUID
    caller_name: str
    company_name: Optional[str]
    vip_level: VIPPriority
    status: VIPStatus
    preferred_agent_id: Optional[uuid.UUID]
    preferred_department_id: Optional[uuid.UUID]
    handling_rules: List[str]
    custom_greeting: Optional[str]
    max_wait_time: int
    callback_priority: int
    email: Optional[str]
    account_number: Optional[str]
    account_value: Optional[float]
    valid_from: datetime
    valid_until: Optional[datetime]
    total_calls: int
    last_call_at: Optional[datetime]
    average_call_duration: int
    satisfaction_score: Optional[float]
    notes: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VIPListResponse(BaseModel):
    """Response model for VIP caller list."""
    vip_callers: List[VIPCallerResponse]
    total: int
    skip: int
    limit: int


class VIPAnalyticsResponse(BaseModel):
    """Response model for VIP analytics."""
    by_vip_level: List[Dict[str, Any]]
    escalation_rate: float
    avg_quality_score: Optional[float]
    top_vip_callers: Optional[List[Dict[str, Any]]]


class BulkImportRequest(BaseModel):
    """Request model for bulk VIP import."""
    vip_callers: List[VIPCallerCreate]


class BulkImportResponse(BaseModel):
    """Response model for bulk import results."""
    total: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]]


# API endpoints
@router.post("/", response_model=VIPCallerResponse, status_code=status.HTTP_201_CREATED)
async def create_vip_caller(
    vip_data: VIPCallerCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Create a new VIP caller.
    
    Creates a new VIP caller with the specified priority level and handling rules.
    The phone number will be hashed for privacy compliance.
    """
    try:
        vip_service = VIPService()
        
        # Convert handling rules to string values
        handling_rules = [rule.value for rule in vip_data.handling_rules]
        
        vip_caller_data = vip_data.dict()
        vip_caller_data['handling_rules'] = handling_rules
        
        vip_caller = await vip_service.create_vip_caller(tenant_id, vip_caller_data)
        
        logger.info(
            "VIP caller created via API",
            tenant_id=str(tenant_id),
            vip_id=str(vip_caller.id),
            caller_name=vip_caller.caller_name
        )
        
        return VIPCallerResponse.from_orm(vip_caller)
        
    except VIPServiceError as e:
        logger.warning("VIP creation failed", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error creating VIP caller", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/", response_model=VIPListResponse)
async def list_vip_callers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    vip_level: Optional[VIPPriority] = Query(None, description="Filter by VIP level"),
    status: Optional[VIPStatus] = Query(None, description="Filter by VIP status"),
    search: Optional[str] = Query(None, description="Search term for name or company"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    List VIP callers with filtering and pagination.
    
    Returns a paginated list of VIP callers with optional filtering by level,
    status, and search terms.
    """
    try:
        vip_service = VIPService()
        
        vip_callers = await vip_service.list_vip_callers(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            vip_level=vip_level,
            status=status,
            search=search
        )
        
        # Get total count for pagination (simplified - in production, use separate count query)
        total = len(vip_callers) + skip  # Approximation
        
        return VIPListResponse(
            vip_callers=[VIPCallerResponse.from_orm(vip) for vip in vip_callers],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error("Failed to list VIP callers", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/{vip_id}", response_model=VIPCallerResponse)
async def get_vip_caller(
    vip_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get VIP caller by ID.
    
    Returns detailed information about a specific VIP caller.
    """
    try:
        vip_service = VIPService()
        vip_caller = await vip_service.get_vip_caller(tenant_id, vip_id)
        
        if not vip_caller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VIP caller not found")
        
        return VIPCallerResponse.from_orm(vip_caller)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get VIP caller", tenant_id=str(tenant_id), vip_id=str(vip_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/{vip_id}", response_model=VIPCallerResponse)
async def update_vip_caller(
    vip_id: uuid.UUID,
    update_data: VIPCallerUpdate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Update VIP caller information.
    
    Updates the specified VIP caller with the provided data.
    Only non-null fields will be updated.
    """
    try:
        vip_service = VIPService()
        
        # Convert update data to dict and remove None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        # Convert handling rules to string values if present
        if 'handling_rules' in update_dict:
            update_dict['handling_rules'] = [rule.value for rule in update_dict['handling_rules']]
        
        vip_caller = await vip_service.update_vip_caller(tenant_id, vip_id, update_dict)
        
        if not vip_caller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VIP caller not found")
        
        logger.info(
            "VIP caller updated via API",
            tenant_id=str(tenant_id),
            vip_id=str(vip_id),
            updated_fields=list(update_dict.keys())
        )
        
        return VIPCallerResponse.from_orm(vip_caller)
        
    except VIPNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VIP caller not found")
    except VIPServiceError as e:
        logger.warning("VIP update failed", tenant_id=str(tenant_id), vip_id=str(vip_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error updating VIP caller", tenant_id=str(tenant_id), vip_id=str(vip_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/{vip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vip_caller(
    vip_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Delete VIP caller.
    
    Permanently deletes the specified VIP caller and all associated data.
    """
    try:
        vip_service = VIPService()
        success = await vip_service.delete_vip_caller(tenant_id, vip_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VIP caller not found")
        
        logger.info("VIP caller deleted via API", tenant_id=str(tenant_id), vip_id=str(vip_id))
        
    except VIPNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VIP caller not found")
    except VIPServiceError as e:
        logger.warning("VIP deletion failed", tenant_id=str(tenant_id), vip_id=str(vip_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error deleting VIP caller", tenant_id=str(tenant_id), vip_id=str(vip_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/identify")
async def identify_vip_caller(
    phone_number: str = Query(..., description="Phone number to check for VIP status"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Identify if a caller is VIP based on phone number.
    
    Used by the call routing system to determine if special VIP handling
    should be applied to an incoming call.
    """
    try:
        vip_service = VIPService()
        vip_caller = await vip_service.identify_vip_caller(tenant_id, phone_number)
        
        if vip_caller:
            priority = await vip_service.get_vip_routing_priority(tenant_id, vip_caller)
            
            return {
                "is_vip": True,
                "vip_caller": VIPCallerResponse.from_orm(vip_caller),
                "routing_priority": priority
            }
        else:
            return {
                "is_vip": False,
                "vip_caller": None,
                "routing_priority": 0
            }
        
    except Exception as e:
        logger.error("Failed to identify VIP caller", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/{vip_id}/analytics", response_model=VIPAnalyticsResponse)
async def get_vip_analytics(
    vip_id: uuid.UUID,
    start_date: Optional[datetime] = Query(None, description="Start date for analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics period"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get analytics for a specific VIP caller.
    
    Returns detailed analytics and metrics for the specified VIP caller
    within the given date range.
    """
    try:
        vip_service = VIPService()
        analytics = await vip_service.get_vip_analytics(
            tenant_id=tenant_id,
            vip_id=vip_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return VIPAnalyticsResponse(**analytics)
        
    except Exception as e:
        logger.error("Failed to get VIP analytics", tenant_id=str(tenant_id), vip_id=str(vip_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/analytics/overview", response_model=VIPAnalyticsResponse)
async def get_vip_overview_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics period"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get overview analytics for all VIP callers.
    
    Returns aggregated analytics and metrics for all VIP callers
    within the given date range.
    """
    try:
        vip_service = VIPService()
        analytics = await vip_service.get_vip_analytics(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return VIPAnalyticsResponse(**analytics)
        
    except Exception as e:
        logger.error("Failed to get VIP overview analytics", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/bulk-import", response_model=BulkImportResponse)
async def bulk_import_vip_callers(
    import_data: BulkImportRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Bulk import VIP callers.
    
    Imports multiple VIP callers from a list. Returns a summary of
    successful and failed imports with error details.
    """
    try:
        vip_service = VIPService()
        
        # Convert VIP data to dictionaries
        vip_data_list = []
        for vip_data in import_data.vip_callers:
            vip_dict = vip_data.dict()
            vip_dict['handling_rules'] = [rule.value for rule in vip_data.handling_rules]
            vip_data_list.append(vip_dict)
        
        results = await vip_service.bulk_import_vips(tenant_id, vip_data_list)
        
        logger.info(
            "VIP bulk import completed via API",
            tenant_id=str(tenant_id),
            total=results['total'],
            successful=results['successful'],
            failed=results['failed']
        )
        
        return BulkImportResponse(**results)
        
    except Exception as e:
        logger.error("VIP bulk import failed", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/{vip_id}/escalation-check")
async def check_vip_escalation(
    vip_id: uuid.UUID,
    wait_time: int = Query(..., description="Current wait time in seconds"),
    queue_position: int = Query(..., description="Current queue position"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Check if VIP escalation rules should be triggered.
    
    Used by the call routing system to determine if a VIP call
    should be escalated based on wait time and queue position.
    """
    try:
        vip_service = VIPService()
        
        # Get VIP caller
        vip_caller = await vip_service.get_vip_caller(tenant_id, vip_id)
        if not vip_caller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VIP caller not found")
        
        # Check escalation rules
        triggered_rules = await vip_service.check_escalation_rules(
            tenant_id, vip_caller, wait_time, queue_position
        )
        
        return {
            "should_escalate": len(triggered_rules) > 0,
            "triggered_rules": [
                {
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "escalation_type": rule.escalation_type,
                    "notification_emails": rule.notification_emails
                }
                for rule in triggered_rules
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check VIP escalation", tenant_id=str(tenant_id), vip_id=str(vip_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")