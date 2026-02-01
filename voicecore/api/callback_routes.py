"""
Callback request API routes for VoiceCore AI.

Provides REST API endpoints for managing callback requests, scheduling,
and automated execution in the multitenant system.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from voicecore.services.callback_service import CallbackService, CallbackServiceError, CallbackNotFoundError, CallbackSchedulingError
from voicecore.models import CallbackStatus, CallbackPriority, CallbackType
from voicecore.middleware import get_current_tenant_id
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/callbacks", tags=["Callback Management"])


# Pydantic models for request/response
class CallbackRequestCreate(BaseModel):
    """Request model for creating callback request."""
    original_call_id: Optional[uuid.UUID] = Field(None, description="Original call that triggered callback")
    caller_number: str = Field(..., description="Caller's phone number")
    caller_name: Optional[str] = Field(None, max_length=255, description="Caller's name")
    caller_email: Optional[str] = Field(None, description="Caller's email for notifications")
    callback_reason: Optional[str] = Field(None, description="Reason for callback request")
    callback_type: CallbackType = Field(CallbackType.GENERAL, description="Type of callback")
    priority: CallbackPriority = Field(CallbackPriority.NORMAL, description="Callback priority")
    requested_time: Optional[datetime] = Field(None, description="Caller's preferred callback time")
    time_window_start: Optional[datetime] = Field(None, description="Start of acceptable time window")
    time_window_end: Optional[datetime] = Field(None, description="End of acceptable time window")
    timezone: str = Field("UTC", description="Caller's timezone")
    department_id: Optional[uuid.UUID] = Field(None, description="Department to handle callback")
    preferred_agent_id: Optional[uuid.UUID] = Field(None, description="Preferred agent for callback")
    max_attempts: int = Field(3, ge=1, le=10, description="Maximum callback attempts")
    sms_notifications: bool = Field(False, description="Enable SMS notifications")
    email_notifications: bool = Field(False, description="Enable email notifications")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('caller_email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('time_window_end')
    def validate_time_window(cls, v, values):
        if v and 'time_window_start' in values and values['time_window_start']:
            if v <= values['time_window_start']:
                raise ValueError('time_window_end must be after time_window_start')
        return v


class CallbackRequestUpdate(BaseModel):
    """Request model for updating callback request."""
    caller_name: Optional[str] = Field(None, max_length=255)
    caller_email: Optional[str] = None
    callback_reason: Optional[str] = None
    callback_type: Optional[CallbackType] = None
    priority: Optional[CallbackPriority] = None
    requested_time: Optional[datetime] = None
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    department_id: Optional[uuid.UUID] = None
    preferred_agent_id: Optional[uuid.UUID] = None
    max_attempts: Optional[int] = Field(None, ge=1, le=10)
    sms_notifications: Optional[bool] = None
    email_notifications: Optional[bool] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CallbackScheduleRequest(BaseModel):
    """Request model for scheduling callback."""
    scheduled_time: datetime = Field(..., description="When to schedule the callback")
    agent_id: Optional[uuid.UUID] = Field(None, description="Specific agent to assign")


class CallbackAttemptComplete(BaseModel):
    """Request model for completing callback attempt."""
    outcome: str = Field(..., description="Attempt outcome")
    call_id: Optional[uuid.UUID] = Field(None, description="Reference to actual call if connected")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Call duration if connected")
    caller_reached: bool = Field(False, description="Whether caller was reached")
    issue_resolved: Optional[bool] = Field(None, description="Whether issue was resolved")
    agent_notes: Optional[str] = Field(None, description="Agent notes")
    caller_feedback: Optional[str] = Field(None, description="Caller feedback")


class CallbackRequestResponse(BaseModel):
    """Response model for callback request."""
    id: uuid.UUID
    original_call_id: Optional[uuid.UUID]
    caller_name: Optional[str]
    caller_email: Optional[str]
    callback_reason: Optional[str]
    callback_type: CallbackType
    priority: CallbackPriority
    status: CallbackStatus
    requested_time: Optional[datetime]
    scheduled_time: Optional[datetime]
    time_window_start: Optional[datetime]
    time_window_end: Optional[datetime]
    timezone: str
    department_id: Optional[uuid.UUID]
    assigned_agent_id: Optional[uuid.UUID]
    preferred_agent_id: Optional[uuid.UUID]
    attempts: int
    max_attempts: int
    last_attempt_at: Optional[datetime]
    next_attempt_at: Optional[datetime]
    completed_at: Optional[datetime]
    outcome: Optional[str]
    resolution_achieved: Optional[bool]
    follow_up_required: bool
    sms_notifications: bool
    email_notifications: bool
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CallbackListResponse(BaseModel):
    """Response model for callback request list."""
    callbacks: List[CallbackRequestResponse]
    total: int
    skip: int
    limit: int


class CallbackAnalyticsResponse(BaseModel):
    """Response model for callback analytics."""
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    total_callbacks: int
    resolved_callbacks: int
    success_rate: float
    avg_attempts: float
    avg_duration: float


# API endpoints
@router.post("/", response_model=CallbackRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_callback_request(
    callback_data: CallbackRequestCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Create a new callback request.
    
    Creates a callback request for a caller who prefers to be called back
    rather than waiting in queue. The system will automatically schedule
    and execute the callback based on availability and preferences.
    """
    try:
        callback_service = CallbackService()
        
        callback_request = await callback_service.create_callback_request(
            tenant_id, callback_data.dict()
        )
        
        logger.info(
            "Callback request created via API",
            tenant_id=str(tenant_id),
            callback_id=str(callback_request.id),
            caller_name=callback_request.caller_name
        )
        
        return CallbackRequestResponse.from_orm(callback_request)
        
    except CallbackServiceError as e:
        logger.warning("Callback creation failed", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error creating callback request", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/", response_model=CallbackListResponse)
async def list_callback_requests(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[CallbackStatus] = Query(None, description="Filter by callback status"),
    priority: Optional[CallbackPriority] = Query(None, description="Filter by callback priority"),
    callback_type: Optional[CallbackType] = Query(None, description="Filter by callback type"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    agent_id: Optional[uuid.UUID] = Query(None, description="Filter by assigned agent"),
    search: Optional[str] = Query(None, description="Search term for caller name or reason"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    List callback requests with filtering and pagination.
    
    Returns a paginated list of callback requests with optional filtering
    by status, priority, type, department, agent, and search terms.
    """
    try:
        callback_service = CallbackService()
        
        callbacks = await callback_service.list_callback_requests(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            status=status,
            priority=priority,
            callback_type=callback_type,
            department_id=department_id,
            agent_id=agent_id,
            search=search
        )
        
        # Get total count for pagination (simplified - in production, use separate count query)
        total = len(callbacks) + skip  # Approximation
        
        return CallbackListResponse(
            callbacks=[CallbackRequestResponse.from_orm(cb) for cb in callbacks],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error("Failed to list callback requests", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/{callback_id}", response_model=CallbackRequestResponse)
async def get_callback_request(
    callback_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get callback request by ID.
    
    Returns detailed information about a specific callback request.
    """
    try:
        callback_service = CallbackService()
        callback_request = await callback_service.get_callback_request(tenant_id, callback_id)
        
        if not callback_request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Callback request not found")
        
        return CallbackRequestResponse.from_orm(callback_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get callback request", tenant_id=str(tenant_id), callback_id=str(callback_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/{callback_id}", response_model=CallbackRequestResponse)
async def update_callback_request(
    callback_id: uuid.UUID,
    update_data: CallbackRequestUpdate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Update callback request information.
    
    Updates the specified callback request with the provided data.
    Only non-null fields will be updated.
    """
    try:
        callback_service = CallbackService()
        
        # Get existing callback request
        callback_request = await callback_service.get_callback_request(tenant_id, callback_id)
        if not callback_request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Callback request not found")
        
        # Convert update data to dict and remove None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        # Update callback request (simplified - in production, implement proper update method)
        for field, value in update_dict.items():
            if hasattr(callback_request, field):
                setattr(callback_request, field, value)
        
        logger.info(
            "Callback request updated via API",
            tenant_id=str(tenant_id),
            callback_id=str(callback_id),
            updated_fields=list(update_dict.keys())
        )
        
        return CallbackRequestResponse.from_orm(callback_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error updating callback request", tenant_id=str(tenant_id), callback_id=str(callback_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/{callback_id}/schedule", response_model=CallbackRequestResponse)
async def schedule_callback(
    callback_id: uuid.UUID,
    schedule_data: CallbackScheduleRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Schedule a callback request for a specific time.
    
    Schedules the callback for the specified time and optionally
    assigns it to a specific agent.
    """
    try:
        callback_service = CallbackService()
        
        success = await callback_service.schedule_callback(
            tenant_id=tenant_id,
            callback_id=callback_id,
            scheduled_time=schedule_data.scheduled_time,
            agent_id=schedule_data.agent_id
        )
        
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to schedule callback")
        
        # Get updated callback request
        callback_request = await callback_service.get_callback_request(tenant_id, callback_id)
        
        logger.info(
            "Callback scheduled via API",
            tenant_id=str(tenant_id),
            callback_id=str(callback_id),
            scheduled_time=schedule_data.scheduled_time.isoformat()
        )
        
        return CallbackRequestResponse.from_orm(callback_request)
        
    except CallbackNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Callback request not found")
    except CallbackSchedulingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error scheduling callback", tenant_id=str(tenant_id), callback_id=str(callback_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/{callback_id}/execute")
async def execute_callback(
    callback_id: uuid.UUID,
    agent_id: uuid.UUID = Query(..., description="Agent executing the callback"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Execute a callback attempt.
    
    Initiates a callback attempt by the specified agent.
    Returns the attempt ID for tracking the execution.
    """
    try:
        callback_service = CallbackService()
        
        attempt = await callback_service.execute_callback(
            tenant_id=tenant_id,
            callback_id=callback_id,
            agent_id=agent_id
        )
        
        logger.info(
            "Callback execution started via API",
            tenant_id=str(tenant_id),
            callback_id=str(callback_id),
            agent_id=str(agent_id),
            attempt_id=str(attempt.id)
        )
        
        return {
            "attempt_id": str(attempt.id),
            "attempt_number": attempt.attempt_number,
            "status": "initiated"
        }
        
    except CallbackNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Callback request not found")
    except CallbackServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error executing callback", tenant_id=str(tenant_id), callback_id=str(callback_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/attempts/{attempt_id}/complete")
async def complete_callback_attempt(
    attempt_id: uuid.UUID,
    completion_data: CallbackAttemptComplete,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Complete a callback attempt with results.
    
    Records the outcome of a callback attempt including whether
    the caller was reached and if their issue was resolved.
    """
    try:
        callback_service = CallbackService()
        
        success = await callback_service.complete_callback_attempt(
            tenant_id=tenant_id,
            attempt_id=attempt_id,
            outcome=completion_data.outcome,
            call_id=completion_data.call_id,
            duration_seconds=completion_data.duration_seconds,
            caller_reached=completion_data.caller_reached,
            issue_resolved=completion_data.issue_resolved,
            agent_notes=completion_data.agent_notes,
            caller_feedback=completion_data.caller_feedback
        )
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Callback attempt not found")
        
        logger.info(
            "Callback attempt completed via API",
            tenant_id=str(tenant_id),
            attempt_id=str(attempt_id),
            outcome=completion_data.outcome
        )
        
        return {"status": "completed", "outcome": completion_data.outcome}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error completing callback attempt", tenant_id=str(tenant_id), attempt_id=str(attempt_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/{callback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_callback(
    callback_id: uuid.UUID,
    reason: str = Query("cancelled_by_user", description="Cancellation reason"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Cancel a callback request.
    
    Cancels a pending or scheduled callback request.
    Cannot cancel callbacks that are already in progress or completed.
    """
    try:
        callback_service = CallbackService()
        
        success = await callback_service.cancel_callback(
            tenant_id=tenant_id,
            callback_id=callback_id,
            reason=reason
        )
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Callback request not found or cannot be cancelled")
        
        logger.info("Callback cancelled via API", tenant_id=str(tenant_id), callback_id=str(callback_id), reason=reason)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error cancelling callback", tenant_id=str(tenant_id), callback_id=str(callback_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/pending/list")
async def get_pending_callbacks(
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    agent_id: Optional[uuid.UUID] = Query(None, description="Filter by assigned agent"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of callbacks to return"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get pending callbacks ready for execution.
    
    Returns callbacks that are scheduled for now or overdue,
    ordered by priority and scheduled time.
    """
    try:
        callback_service = CallbackService()
        
        pending_callbacks = await callback_service.get_pending_callbacks(
            tenant_id=tenant_id,
            department_id=department_id,
            agent_id=agent_id,
            limit=limit
        )
        
        return {
            "pending_callbacks": [CallbackRequestResponse.from_orm(cb) for cb in pending_callbacks],
            "count": len(pending_callbacks)
        }
        
    except Exception as e:
        logger.error("Failed to get pending callbacks", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/analytics/overview", response_model=CallbackAnalyticsResponse)
async def get_callback_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics period"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get callback analytics and metrics.
    
    Returns comprehensive analytics including success rates,
    callback volume by status and type, and performance metrics.
    """
    try:
        callback_service = CallbackService()
        
        analytics = await callback_service.get_callback_analytics(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            department_id=department_id
        )
        
        return CallbackAnalyticsResponse(**analytics)
        
    except Exception as e:
        logger.error("Failed to get callback analytics", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")