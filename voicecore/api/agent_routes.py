"""
Agent management API routes for VoiceCore AI.

Provides comprehensive REST API endpoints for agent lifecycle management,
status tracking, and department hierarchy with enterprise-grade validation.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from voicecore.services.agent_service import (
    AgentService, AgentServiceError, AgentNotFoundError, 
    AgentAlreadyExistsError, InvalidAgentStatusError, DepartmentNotFoundError
)
from voicecore.models import AgentStatus
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


# Pydantic models for request/response validation
class AgentCreateRequest(BaseModel):
    """Request model for creating an agent."""
    email: str = Field(..., description="Agent email address")
    name: str = Field(..., min_length=1, max_length=255, description="Agent full name")
    first_name: Optional[str] = Field(None, max_length=100, description="Agent first name")
    last_name: Optional[str] = Field(None, max_length=100, description="Agent last name")
    extension: str = Field(..., min_length=3, max_length=10, description="Numeric extension")
    phone_number: Optional[str] = Field(None, max_length=20, description="Agent phone number")
    department_id: uuid.UUID = Field(..., description="Department UUID")
    is_manager: bool = Field(False, description="Whether agent is a manager")
    manager_id: Optional[uuid.UUID] = Field(None, description="Manager agent UUID")
    is_active: bool = Field(True, description="Whether agent is active")
    work_schedule: Dict[str, Any] = Field(default_factory=dict, description="Work schedule configuration")
    is_afterhours: bool = Field(False, description="Whether agent works afterhours")
    max_concurrent_calls: int = Field(1, ge=1, le=10, description="Maximum concurrent calls")
    auto_answer: bool = Field(False, description="Auto-answer incoming calls")
    skills: List[str] = Field(default_factory=list, description="Agent skills")
    languages: List[str] = Field(default_factory=lambda: ["en"], description="Supported languages")
    routing_weight: int = Field(1, ge=1, le=10, description="Routing weight")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Agent settings")
    initial_status: Optional[str] = Field(None, description="Initial agent status")
    
    @validator('extension')
    def validate_extension(cls, v):
        if not v.isdigit():
            raise ValueError('Extension must be numeric')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v or '.' not in v:
            raise ValueError('Invalid email format')
        return v.lower()


class AgentUpdateRequest(BaseModel):
    """Request model for updating an agent."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    department_id: Optional[uuid.UUID] = None
    is_manager: Optional[bool] = None
    manager_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    work_schedule: Optional[Dict[str, Any]] = None
    is_afterhours: Optional[bool] = None
    max_concurrent_calls: Optional[int] = Field(None, ge=1, le=10)
    auto_answer: Optional[bool] = None
    skills: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    routing_weight: Optional[int] = Field(None, ge=1, le=10)
    settings: Optional[Dict[str, Any]] = None


class AgentStatusUpdateRequest(BaseModel):
    """Request model for updating agent status."""
    status: str = Field(..., description="New agent status")
    session_type: str = Field("web", description="Session type")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = [status.value for status in AgentStatus]
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v


class AgentResponse(BaseModel):
    """Response model for agent data."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    name: str
    first_name: str
    last_name: str
    extension: str
    phone_number: Optional[str]
    department_id: uuid.UUID
    department_name: Optional[str]
    is_manager: bool
    manager_id: Optional[uuid.UUID]
    status: str
    is_active: bool
    last_status_change: Optional[datetime]
    work_schedule: Dict[str, Any]
    is_afterhours: bool
    max_concurrent_calls: int
    current_calls: int
    last_call_at: Optional[datetime]
    routing_weight: int
    auto_answer: bool
    skills: List[str]
    languages: List[str]
    total_calls_handled: int
    average_call_duration: int
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    """Response model for agent list."""
    agents: List[AgentResponse]
    total: int
    skip: int
    limit: int


class AgentMetricsResponse(BaseModel):
    """Response model for agent metrics."""
    agent_id: uuid.UUID
    agent_name: str
    period_start: str
    period_end: str
    calls: Dict[str, Any]
    sessions: Dict[str, Any]
    current_status: str
    current_calls: int
    last_activity: Optional[str]


# Dependency for getting agent service
def get_agent_service() -> AgentService:
    """Dependency to get agent service instance."""
    return AgentService()


# Dependency for tenant ID (placeholder - would be extracted from auth)
def get_tenant_id() -> uuid.UUID:
    """Dependency to get current tenant ID from authentication context."""
    # TODO: Extract from JWT token or session
    return uuid.uuid4()  # Placeholder


@router.post("/", response_model=AgentResponse, status_code=HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreateRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Create a new agent.
    
    Creates a new agent with the specified configuration and assigns them
    to a department with proper validation and security checks.
    """
    try:
        agent = await agent_service.create_agent(
            tenant_id=tenant_id,
            agent_data=agent_data.dict()
        )
        
        # Convert to response model
        response_data = {
            **agent.__dict__,
            "status": agent.status.value,
            "department_name": agent.department.name if agent.department else None
        }
        
        logger.info(
            "Agent created via API",
            tenant_id=str(tenant_id),
            agent_id=str(agent.id),
            agent_name=agent.name
        )
        
        return AgentResponse(**response_data)
        
    except AgentAlreadyExistsError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except DepartmentNotFoundError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID = Path(..., description="Agent UUID"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Get agent by ID.
    
    Retrieves detailed information about a specific agent including
    their current status, department, and performance metrics.
    """
    try:
        agent = await agent_service.get_agent(tenant_id, agent_id)
        
        if not agent:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Agent not found")
        
        # Convert to response model
        response_data = {
            **agent.__dict__,
            "status": agent.status.value,
            "department_name": agent.department.name if agent.department else None
        }
        
        return AgentResponse(**response_data)
        
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/extension/{extension}", response_model=AgentResponse)
async def get_agent_by_extension(
    extension: str = Path(..., description="Agent extension"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Get agent by extension number.
    
    Retrieves agent information using their extension number,
    useful for call routing and transfer operations.
    """
    try:
        agent = await agent_service.get_agent_by_extension(tenant_id, extension)
        
        if not agent:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Agent not found")
        
        # Convert to response model
        response_data = {
            **agent.__dict__,
            "status": agent.status.value,
            "department_name": agent.department.name if agent.department else None
        }
        
        return AgentResponse(**response_data)
        
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    status: Optional[str] = Query(None, description="Filter by status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    List agents with filtering and pagination.
    
    Retrieves a list of agents with optional filtering by department,
    status, and active state. Supports pagination for large datasets.
    """
    try:
        # Validate status if provided
        agent_status = None
        if status:
            try:
                agent_status = AgentStatus(status)
            except ValueError:
                valid_statuses = [s.value for s in AgentStatus]
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {valid_statuses}"
                )
        
        agents = await agent_service.list_agents(
            tenant_id=tenant_id,
            department_id=department_id,
            status=agent_status,
            is_active=is_active,
            skip=skip,
            limit=limit
        )
        
        # Convert to response models
        agent_responses = []
        for agent in agents:
            response_data = {
                **agent.__dict__,
                "status": agent.status.value,
                "department_name": agent.department.name if agent.department else None
            }
            agent_responses.append(AgentResponse(**response_data))
        
        return AgentListResponse(
            agents=agent_responses,
            total=len(agent_responses),  # TODO: Get actual total count
            skip=skip,
            limit=limit
        )
        
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID = Path(..., description="Agent UUID"),
    update_data: AgentUpdateRequest = Body(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Update agent information.
    
    Updates agent details such as contact information, department assignment,
    skills, and configuration settings with proper validation.
    """
    try:
        # Filter out None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        agent = await agent_service.update_agent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            update_data=update_dict
        )
        
        if not agent:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Agent not found")
        
        # Convert to response model
        response_data = {
            **agent.__dict__,
            "status": agent.status.value,
            "department_name": agent.department.name if agent.department else None
        }
        
        logger.info(
            "Agent updated via API",
            tenant_id=str(tenant_id),
            agent_id=str(agent_id),
            updated_fields=list(update_dict.keys())
        )
        
        return AgentResponse(**response_data)
        
    except AgentNotFoundError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{agent_id}/status", response_model=dict)
async def update_agent_status(
    agent_id: uuid.UUID = Path(..., description="Agent UUID"),
    status_data: AgentStatusUpdateRequest = Body(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Update agent status.
    
    Updates agent availability status (available, busy, not_available)
    with session tracking for analytics and monitoring.
    """
    try:
        new_status = AgentStatus(status_data.status)
        
        success = await agent_service.update_agent_status(
            tenant_id=tenant_id,
            agent_id=agent_id,
            new_status=new_status,
            session_type=status_data.session_type
        )
        
        if not success:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Status update failed")
        
        logger.info(
            "Agent status updated via API",
            tenant_id=str(tenant_id),
            agent_id=str(agent_id),
            new_status=status_data.status,
            session_type=status_data.session_type
        )
        
        return {
            "success": True,
            "message": "Agent status updated successfully",
            "agent_id": str(agent_id),
            "new_status": status_data.status
        }
        
    except AgentNotFoundError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidAgentStatusError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/available/list", response_model=List[AgentResponse])
async def get_available_agents(
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    skills: Optional[str] = Query(None, description="Required skills (comma-separated)"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Get available agents.
    
    Retrieves all agents currently available for call assignment,
    optionally filtered by department and required skills.
    """
    try:
        # Parse skills if provided
        required_skills = None
        if skills:
            required_skills = [skill.strip() for skill in skills.split(',')]
        
        agents = await agent_service.get_available_agents(
            tenant_id=tenant_id,
            department_id=department_id,
            required_skills=required_skills
        )
        
        # Convert to response models
        agent_responses = []
        for agent in agents:
            response_data = {
                **agent.__dict__,
                "status": agent.status.value,
                "department_name": agent.department.name if agent.department else None
            }
            agent_responses.append(AgentResponse(**response_data))
        
        return agent_responses
        
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{agent_id}/metrics", response_model=AgentMetricsResponse)
async def get_agent_metrics(
    agent_id: uuid.UUID = Path(..., description="Agent UUID"),
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Get agent performance metrics.
    
    Retrieves detailed performance metrics for an agent including
    call statistics, session data, and availability metrics.
    """
    try:
        metrics = await agent_service.get_agent_metrics(
            tenant_id=tenant_id,
            agent_id=agent_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if not metrics:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Agent not found")
        
        return AgentMetricsResponse(**metrics)
        
    except AgentNotFoundError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{agent_id}/assign-call", response_model=dict)
async def assign_call_to_agent(
    agent_id: uuid.UUID = Path(..., description="Agent UUID"),
    call_id: uuid.UUID = Body(..., embed=True, description="Call UUID"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Assign a call to an agent.
    
    Assigns an active call to a specific agent and updates their
    status and call count accordingly.
    """
    try:
        success = await agent_service.assign_call_to_agent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            call_id=call_id
        )
        
        if not success:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Call assignment failed")
        
        logger.info(
            "Call assigned to agent via API",
            tenant_id=str(tenant_id),
            agent_id=str(agent_id),
            call_id=str(call_id)
        )
        
        return {
            "success": True,
            "message": "Call assigned successfully",
            "agent_id": str(agent_id),
            "call_id": str(call_id)
        }
        
    except AgentNotFoundError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{agent_id}/release-call", response_model=dict)
async def release_call_from_agent(
    agent_id: uuid.UUID = Path(..., description="Agent UUID"),
    call_id: uuid.UUID = Body(..., embed=True, description="Call UUID"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Release a call from an agent.
    
    Releases a call from an agent and updates their status
    and availability accordingly.
    """
    try:
        success = await agent_service.release_call_from_agent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            call_id=call_id
        )
        
        if not success:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Call release failed")
        
        logger.info(
            "Call released from agent via API",
            tenant_id=str(tenant_id),
            agent_id=str(agent_id),
            call_id=str(call_id)
        )
        
        return {
            "success": True,
            "message": "Call released successfully",
            "agent_id": str(agent_id),
            "call_id": str(call_id)
        }
        
    except AgentNotFoundError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{agent_id}", response_model=dict)
async def delete_agent(
    agent_id: uuid.UUID = Path(..., description="Agent UUID"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Delete an agent.
    
    Performs a soft delete of an agent by marking them as inactive.
    Agent must not have any active calls to be deleted.
    """
    try:
        success = await agent_service.delete_agent(
            tenant_id=tenant_id,
            agent_id=agent_id
        )
        
        if not success:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Agent deletion failed")
        
        logger.info(
            "Agent deleted via API",
            tenant_id=str(tenant_id),
            agent_id=str(agent_id)
        )
        
        return {
            "success": True,
            "message": "Agent deleted successfully",
            "agent_id": str(agent_id)
        }
        
    except AgentNotFoundError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except AgentServiceError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/health/status", response_model=dict)
async def agent_service_health():
    """
    Health check endpoint for agent service.
    
    Returns the health status of the agent management service
    for monitoring and load balancing purposes.
    """
    return {
        "status": "healthy",
        "service": "agent-management",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": [
            "POST /api/v1/agents/",
            "GET /api/v1/agents/{agent_id}",
            "GET /api/v1/agents/extension/{extension}",
            "GET /api/v1/agents/",
            "PUT /api/v1/agents/{agent_id}",
            "PATCH /api/v1/agents/{agent_id}/status",
            "GET /api/v1/agents/available/list",
            "GET /api/v1/agents/{agent_id}/metrics",
            "POST /api/v1/agents/{agent_id}/assign-call",
            "POST /api/v1/agents/{agent_id}/release-call",
            "DELETE /api/v1/agents/{agent_id}"
        ]
    }