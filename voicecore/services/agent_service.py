"""
Agent management service for VoiceCore AI.

Provides comprehensive agent lifecycle management with status tracking,
department hierarchy, and real-time availability management for the
multitenant virtual receptionist system.
"""

import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload, joinedload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    Agent, Department, AgentSession, AgentStatus, 
    Call, CallStatus, AgentMetrics
)
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils


logger = get_logger(__name__)


class AgentServiceError(Exception):
    """Base exception for agent service errors."""
    pass


class AgentNotFoundError(AgentServiceError):
    """Raised when an agent is not found."""
    pass


class AgentAlreadyExistsError(AgentServiceError):
    """Raised when trying to create an agent that already exists."""
    pass


class InvalidAgentStatusError(AgentServiceError):
    """Raised when trying to set an invalid agent status."""
    pass


class DepartmentNotFoundError(AgentServiceError):
    """Raised when a department is not found."""
    pass


class AgentService:
    """
    Comprehensive agent management service.
    
    Handles agent lifecycle, status management, department hierarchy,
    and real-time availability tracking with enterprise-grade features.
    """
    
    def __init__(self):
        self.logger = logger
    
    async def create_agent(
        self, 
        tenant_id: uuid.UUID, 
        agent_data: Dict[str, Any]
    ) -> Agent:
        """
        Create a new agent with complete setup.
        
        Args:
            tenant_id: Tenant UUID
            agent_data: Dictionary containing agent information
            
        Returns:
            Agent: Created agent instance
            
        Raises:
            AgentAlreadyExistsError: If agent already exists
            DepartmentNotFoundError: If department doesn't exist
            AgentServiceError: If creation fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Verify department exists
                department_id = agent_data.get("department_id")
                if department_id:
                    dept_result = await session.execute(
                        select(Department).where(
                            and_(
                                Department.id == department_id,
                                Department.tenant_id == tenant_id,
                                Department.is_active == True
                            )
                        )
                    )
                    department = dept_result.scalar_one_or_none()
                    if not department:
                        raise DepartmentNotFoundError(f"Department {department_id} not found")
                
                # Check if agent already exists (by email or extension)
                existing_agent = await self._check_agent_exists(
                    session, tenant_id, 
                    agent_data.get("email"), 
                    agent_data.get("extension")
                )
                
                if existing_agent:
                    raise AgentAlreadyExistsError(
                        f"Agent already exists with email '{agent_data.get('email')}' "
                        f"or extension '{agent_data.get('extension')}'"
                    )
                
                # Create agent
                agent = Agent(
                    tenant_id=tenant_id,
                    email=agent_data["email"],
                    name=agent_data["name"],
                    first_name=agent_data.get("first_name", agent_data["name"].split()[0]),
                    last_name=agent_data.get("last_name", " ".join(agent_data["name"].split()[1:])),
                    extension=agent_data["extension"],
                    phone_number=agent_data.get("phone_number"),
                    department_id=department_id,
                    is_manager=agent_data.get("is_manager", False),
                    manager_id=agent_data.get("manager_id"),
                    status=AgentStatus.NOT_AVAILABLE,  # Start as not available
                    is_active=agent_data.get("is_active", True),
                    work_schedule=agent_data.get("work_schedule", {}),
                    is_afterhours=agent_data.get("is_afterhours", False),
                    max_concurrent_calls=agent_data.get("max_concurrent_calls", 1),
                    auto_answer=agent_data.get("auto_answer", False),
                    skills=agent_data.get("skills", []),
                    languages=agent_data.get("languages", ["en"]),
                    routing_weight=agent_data.get("routing_weight", 1),
                    settings=agent_data.get("settings", {})
                )
                
                session.add(agent)
                await session.flush()  # Get the agent ID
                
                # Create initial agent session if agent is being created as available
                if agent_data.get("initial_status") == "available":
                    await self._create_agent_session(session, agent.id, AgentStatus.AVAILABLE)
                    agent.status = AgentStatus.AVAILABLE
                    agent.last_status_change = datetime.utcnow()
                
                await session.commit()
                
                self.logger.info(
                    "Agent created successfully",
                    tenant_id=str(tenant_id),
                    agent_id=str(agent.id),
                    agent_name=agent.name,
                    extension=agent.extension,
                    department_id=str(department_id) if department_id else None
                )
                
                return agent
                
        except (AgentAlreadyExistsError, DepartmentNotFoundError):
            raise
        except IntegrityError as e:
            self.logger.error("Agent creation failed due to constraint violation", error=str(e))
            raise AgentAlreadyExistsError("Agent with this email or extension already exists")
        except Exception as e:
            self.logger.error("Agent creation failed", error=str(e))
            raise AgentServiceError(f"Failed to create agent: {str(e)}")
    
    async def get_agent(
        self, 
        tenant_id: uuid.UUID, 
        agent_id: uuid.UUID
    ) -> Optional[Agent]:
        """
        Get agent by ID with department information.
        
        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID
            
        Returns:
            Optional[Agent]: Agent instance or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(Agent)
                    .options(joinedload(Agent.department))
                    .where(
                        and_(
                            Agent.id == agent_id,
                            Agent.tenant_id == tenant_id
                        )
                    )
                )
                agent = result.scalar_one_or_none()
                
                if agent:
                    self.logger.debug("Agent retrieved", agent_id=str(agent_id))
                
                return agent
                
        except Exception as e:
            self.logger.error("Failed to get agent", agent_id=str(agent_id), error=str(e))
            return None
    
    async def get_agent_by_extension(
        self, 
        tenant_id: uuid.UUID, 
        extension: str
    ) -> Optional[Agent]:
        """
        Get agent by extension number.
        
        Args:
            tenant_id: Tenant UUID
            extension: Agent extension
            
        Returns:
            Optional[Agent]: Agent instance or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(Agent)
                    .options(joinedload(Agent.department))
                    .where(
                        and_(
                            Agent.extension == extension,
                            Agent.tenant_id == tenant_id,
                            Agent.is_active == True
                        )
                    )
                )
                agent = result.scalar_one_or_none()
                
                return agent
                
        except Exception as e:
            self.logger.error("Failed to get agent by extension", extension=extension, error=str(e))
            return None
    
    async def list_agents(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[AgentStatus] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """
        List agents with filtering and pagination.
        
        Args:
            tenant_id: Tenant UUID
            department_id: Filter by department (optional)
            status: Filter by status (optional)
            is_active: Filter by active status (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Agent]: List of agent instances
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                query = select(Agent).options(joinedload(Agent.department))
                
                # Apply filters
                conditions = [Agent.tenant_id == tenant_id]
                
                if department_id:
                    conditions.append(Agent.department_id == department_id)
                
                if status:
                    conditions.append(Agent.status == status)
                
                if is_active is not None:
                    conditions.append(Agent.is_active == is_active)
                
                query = query.where(and_(*conditions))
                query = query.offset(skip).limit(limit).order_by(Agent.name)
                
                result = await session.execute(query)
                agents = result.scalars().all()
                
                self.logger.debug(
                    "Agents listed",
                    tenant_id=str(tenant_id),
                    count=len(agents),
                    department_id=str(department_id) if department_id else None,
                    status=status.value if status else None
                )
                
                return list(agents)
                
        except Exception as e:
            self.logger.error("Failed to list agents", error=str(e))
            return []
    
    async def update_agent(
        self,
        tenant_id: uuid.UUID,
        agent_id: uuid.UUID,
        update_data: Dict[str, Any]
    ) -> Optional[Agent]:
        """
        Update agent information.
        
        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID
            update_data: Dictionary containing fields to update
            
        Returns:
            Optional[Agent]: Updated agent instance or None if not found
            
        Raises:
            AgentNotFoundError: If agent doesn't exist
            AgentServiceError: If update fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get existing agent
                result = await session.execute(
                    select(Agent).where(
                        and_(
                            Agent.id == agent_id,
                            Agent.tenant_id == tenant_id
                        )
                    )
                )
                agent = result.scalar_one_or_none()
                
                if not agent:
                    raise AgentNotFoundError(f"Agent {agent_id} not found")
                
                # Update allowed fields
                allowed_fields = [
                    'name', 'first_name', 'last_name', 'phone_number', 'department_id',
                    'is_manager', 'manager_id', 'is_active', 'work_schedule', 'is_afterhours',
                    'max_concurrent_calls', 'auto_answer', 'skills', 'languages', 
                    'routing_weight', 'settings'
                ]
                
                for field, value in update_data.items():
                    if field in allowed_fields and hasattr(agent, field):
                        setattr(agent, field, value)
                
                agent.updated_at = datetime.utcnow()
                await session.commit()
                
                self.logger.info(
                    "Agent updated successfully",
                    tenant_id=str(tenant_id),
                    agent_id=str(agent_id),
                    updated_fields=list(update_data.keys())
                )
                
                return agent
                
        except AgentNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Agent update failed", agent_id=str(agent_id), error=str(e))
            raise AgentServiceError(f"Failed to update agent: {str(e)}")
    
    async def update_agent_status(
        self,
        tenant_id: uuid.UUID,
        agent_id: uuid.UUID,
        new_status: AgentStatus,
        session_type: str = "web"
    ) -> bool:
        """
        Update agent status with session tracking and real-time broadcasting.
        
        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID
            new_status: New agent status
            session_type: Type of session (web, mobile, api)
            
        Returns:
            bool: True if status was updated successfully
            
        Raises:
            AgentNotFoundError: If agent doesn't exist
            InvalidAgentStatusError: If status transition is invalid
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get agent
                result = await session.execute(
                    select(Agent).where(
                        and_(
                            Agent.id == agent_id,
                            Agent.tenant_id == tenant_id
                        )
                    )
                )
                agent = result.scalar_one_or_none()
                
                if not agent:
                    raise AgentNotFoundError(f"Agent {agent_id} not found")
                
                old_status = agent.status
                
                # Validate status transition
                if not self._is_valid_status_transition(old_status, new_status):
                    raise InvalidAgentStatusError(
                        f"Invalid status transition from {old_status.value} to {new_status.value}"
                    )
                
                # Update agent status
                agent.status = new_status
                agent.last_status_change = datetime.utcnow()
                
                # Handle session management
                if new_status == AgentStatus.AVAILABLE:
                    # Start new session or update existing
                    await self._start_or_update_session(session, agent_id, session_type)
                elif old_status == AgentStatus.AVAILABLE and new_status != AgentStatus.AVAILABLE:
                    # End current session
                    await self._end_current_session(session, agent_id, new_status)
                
                await session.commit()
                
                # Broadcast status update via WebSocket
                try:
                    from voicecore.services.websocket_service import websocket_manager
                    await websocket_manager.broadcast_agent_status_update(
                        tenant_id=tenant_id,
                        agent_id=agent_id,
                        status=new_status,
                        additional_data={
                            "agent_name": agent.name,
                            "extension": agent.extension,
                            "department_id": str(agent.department_id) if agent.department_id else None,
                            "session_type": session_type,
                            "current_calls": agent.current_calls
                        }
                    )
                except Exception as ws_error:
                    # Don't fail the status update if WebSocket broadcast fails
                    self.logger.warning(
                        "WebSocket broadcast failed for agent status update",
                        agent_id=str(agent_id),
                        error=str(ws_error)
                    )
                
                self.logger.info(
                    "Agent status updated",
                    tenant_id=str(tenant_id),
                    agent_id=str(agent_id),
                    old_status=old_status.value,
                    new_status=new_status.value,
                    session_type=session_type
                )
                
                return True
                
        except (AgentNotFoundError, InvalidAgentStatusError):
            raise
        except Exception as e:
            self.logger.error("Agent status update failed", agent_id=str(agent_id), error=str(e))
            raise AgentServiceError(f"Failed to update agent status: {str(e)}")
    
    async def get_available_agents(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        required_skills: Optional[List[str]] = None
    ) -> List[Agent]:
        """
        Get all available agents, optionally filtered by department and skills.
        
        Args:
            tenant_id: Tenant UUID
            department_id: Filter by department (optional)
            required_skills: Required skills (optional)
            
        Returns:
            List[Agent]: List of available agents
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                query = select(Agent).options(joinedload(Agent.department))
                
                conditions = [
                    Agent.tenant_id == tenant_id,
                    Agent.is_active == True,
                    Agent.status == AgentStatus.AVAILABLE,
                    Agent.current_calls < Agent.max_concurrent_calls
                ]
                
                if department_id:
                    conditions.append(Agent.department_id == department_id)
                
                query = query.where(and_(*conditions))
                query = query.order_by(Agent.routing_weight.desc(), Agent.last_call_at.asc())
                
                result = await session.execute(query)
                agents = result.scalars().all()
                
                # Filter by skills if specified
                if required_skills:
                    agents = [
                        agent for agent in agents
                        if self._agent_has_skills(agent, required_skills)
                    ]
                
                return list(agents)
                
        except Exception as e:
            self.logger.error("Failed to get available agents", error=str(e))
            return []
    
    async def assign_call_to_agent(
        self,
        tenant_id: uuid.UUID,
        agent_id: uuid.UUID,
        call_id: uuid.UUID
    ) -> bool:
        """
        Assign a call to an agent and update their status.
        
        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID
            call_id: Call UUID
            
        Returns:
            bool: True if assignment was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get agent and verify availability
                agent_result = await session.execute(
                    select(Agent).where(
                        and_(
                            Agent.id == agent_id,
                            Agent.tenant_id == tenant_id
                        )
                    )
                )
                agent = agent_result.scalar_one_or_none()
                
                if not agent:
                    raise AgentNotFoundError(f"Agent {agent_id} not found")
                
                if agent.current_calls >= agent.max_concurrent_calls:
                    self.logger.warning(
                        "Agent at maximum call capacity",
                        agent_id=str(agent_id),
                        current_calls=agent.current_calls,
                        max_calls=agent.max_concurrent_calls
                    )
                    return False
                
                # Update agent call count and status
                agent.current_calls += 1
                agent.last_call_at = datetime.utcnow()
                
                if agent.status == AgentStatus.AVAILABLE:
                    agent.status = AgentStatus.BUSY
                    agent.last_status_change = datetime.utcnow()
                
                # Update call assignment
                await session.execute(
                    update(Call)
                    .where(Call.id == call_id)
                    .values(
                        agent_id=agent_id,
                        status=CallStatus.CONNECTED
                    )
                )
                
                await session.commit()
                
                self.logger.info(
                    "Call assigned to agent",
                    tenant_id=str(tenant_id),
                    agent_id=str(agent_id),
                    call_id=str(call_id),
                    agent_current_calls=agent.current_calls
                )
                
                return True
                
        except AgentNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Call assignment failed", agent_id=str(agent_id), error=str(e))
            return False
    
    async def release_call_from_agent(
        self,
        tenant_id: uuid.UUID,
        agent_id: uuid.UUID,
        call_id: uuid.UUID
    ) -> bool:
        """
        Release a call from an agent and update their status.
        
        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID
            call_id: Call UUID
            
        Returns:
            bool: True if release was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get agent
                agent_result = await session.execute(
                    select(Agent).where(
                        and_(
                            Agent.id == agent_id,
                            Agent.tenant_id == tenant_id
                        )
                    )
                )
                agent = agent_result.scalar_one_or_none()
                
                if not agent:
                    raise AgentNotFoundError(f"Agent {agent_id} not found")
                
                # Update agent call count
                agent.current_calls = max(0, agent.current_calls - 1)
                
                # Update status if no more calls
                if agent.current_calls == 0 and agent.status == AgentStatus.BUSY:
                    agent.status = AgentStatus.AVAILABLE
                    agent.last_status_change = datetime.utcnow()
                
                await session.commit()
                
                self.logger.info(
                    "Call released from agent",
                    tenant_id=str(tenant_id),
                    agent_id=str(agent_id),
                    call_id=str(call_id),
                    agent_current_calls=agent.current_calls
                )
                
                return True
                
        except AgentNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Call release failed", agent_id=str(agent_id), error=str(e))
            return False
    
    async def get_agent_metrics(
        self,
        tenant_id: uuid.UUID,
        agent_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get agent performance metrics.
        
        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID
            start_date: Start date for metrics (optional)
            end_date: End date for metrics (optional)
            
        Returns:
            Dict[str, Any]: Agent metrics
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Set default date range if not provided
                if not end_date:
                    end_date = datetime.utcnow()
                if not start_date:
                    start_date = end_date - timedelta(days=30)
                
                # Get basic agent info
                agent_result = await session.execute(
                    select(Agent).where(
                        and_(
                            Agent.id == agent_id,
                            Agent.tenant_id == tenant_id
                        )
                    )
                )
                agent = agent_result.scalar_one_or_none()
                
                if not agent:
                    raise AgentNotFoundError(f"Agent {agent_id} not found")
                
                # Get call metrics
                call_metrics = await session.execute(
                    select(
                        func.count(Call.id).label('total_calls'),
                        func.avg(Call.duration).label('avg_duration'),
                        func.sum(Call.duration).label('total_talk_time'),
                        func.count(
                            func.case([(Call.status == CallStatus.COMPLETED, 1)])
                        ).label('completed_calls')
                    )
                    .where(
                        and_(
                            Call.agent_id == agent_id,
                            Call.tenant_id == tenant_id,
                            Call.created_at >= start_date,
                            Call.created_at <= end_date
                        )
                    )
                )
                call_stats = call_metrics.fetchone()
                
                # Get session metrics
                session_metrics = await session.execute(
                    select(
                        func.count(AgentSession.id).label('total_sessions'),
                        func.avg(
                            func.extract('epoch', AgentSession.session_end - AgentSession.session_start)
                        ).label('avg_session_duration'),
                        func.sum(
                            func.extract('epoch', AgentSession.session_end - AgentSession.session_start)
                        ).label('total_online_time')
                    )
                    .where(
                        and_(
                            AgentSession.agent_id == agent_id,
                            AgentSession.tenant_id == tenant_id,
                            AgentSession.session_start >= start_date,
                            AgentSession.session_start <= end_date,
                            AgentSession.session_end.isnot(None)
                        )
                    )
                )
                session_stats = session_metrics.fetchone()
                
                return {
                    "agent_id": str(agent_id),
                    "agent_name": agent.name,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "calls": {
                        "total": call_stats[0] or 0,
                        "completed": call_stats[3] or 0,
                        "completion_rate": (call_stats[3] / call_stats[0]) if call_stats[0] else 0,
                        "average_duration": int(call_stats[1] or 0),
                        "total_talk_time": int(call_stats[2] or 0)
                    },
                    "sessions": {
                        "total": session_stats[0] or 0,
                        "average_duration": int(session_stats[1] or 0),
                        "total_online_time": int(session_stats[2] or 0)
                    },
                    "current_status": agent.status.value,
                    "current_calls": agent.current_calls,
                    "last_activity": agent.last_status_change.isoformat() if agent.last_status_change else None
                }
                
        except AgentNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Failed to get agent metrics", agent_id=str(agent_id), error=str(e))
            return {}
    
    async def delete_agent(
        self,
        tenant_id: uuid.UUID,
        agent_id: uuid.UUID
    ) -> bool:
        """
        Delete an agent and handle cleanup.
        
        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            AgentNotFoundError: If agent doesn't exist
            AgentServiceError: If agent has active calls
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get agent
                agent_result = await session.execute(
                    select(Agent).where(
                        and_(
                            Agent.id == agent_id,
                            Agent.tenant_id == tenant_id
                        )
                    )
                )
                agent = agent_result.scalar_one_or_none()
                
                if not agent:
                    raise AgentNotFoundError(f"Agent {agent_id} not found")
                
                # Check for active calls
                if agent.current_calls > 0:
                    raise AgentServiceError("Cannot delete agent with active calls")
                
                # End any active sessions
                await self._end_current_session(session, agent_id, AgentStatus.NOT_AVAILABLE)
                
                # Soft delete - mark as inactive instead of hard delete
                agent.is_active = False
                agent.status = AgentStatus.NOT_AVAILABLE
                agent.updated_at = datetime.utcnow()
                
                await session.commit()
                
                self.logger.info(
                    "Agent deleted (soft delete)",
                    tenant_id=str(tenant_id),
                    agent_id=str(agent_id),
                    agent_name=agent.name
                )
                
                return True
                
        except (AgentNotFoundError, AgentServiceError):
            raise
        except Exception as e:
            self.logger.error("Agent deletion failed", agent_id=str(agent_id), error=str(e))
            raise AgentServiceError(f"Failed to delete agent: {str(e)}")
    
    # Private helper methods
    
    async def _check_agent_exists(
        self,
        session,
        tenant_id: uuid.UUID,
        email: str,
        extension: str
    ) -> Optional[Agent]:
        """Check if agent already exists by email or extension."""
        result = await session.execute(
            select(Agent).where(
                and_(
                    Agent.tenant_id == tenant_id,
                    or_(
                        Agent.email == email,
                        Agent.extension == extension
                    )
                )
            )
        )
        return result.scalar_one_or_none()
    
    def _is_valid_status_transition(
        self,
        old_status: AgentStatus,
        new_status: AgentStatus
    ) -> bool:
        """Validate agent status transitions."""
        # Define valid transitions
        valid_transitions = {
            AgentStatus.NOT_AVAILABLE: [AgentStatus.AVAILABLE],
            AgentStatus.AVAILABLE: [AgentStatus.BUSY, AgentStatus.NOT_AVAILABLE],
            AgentStatus.BUSY: [AgentStatus.AVAILABLE, AgentStatus.NOT_AVAILABLE]
        }
        
        return new_status in valid_transitions.get(old_status, [])
    
    async def _create_agent_session(
        self,
        session,
        agent_id: uuid.UUID,
        initial_status: AgentStatus,
        session_type: str = "web"
    ):
        """Create a new agent session."""
        agent_session = AgentSession(
            agent_id=agent_id,
            session_start=datetime.utcnow(),
            initial_status=initial_status,
            session_type=session_type
        )
        session.add(agent_session)
    
    async def _start_or_update_session(
        self,
        session,
        agent_id: uuid.UUID,
        session_type: str
    ):
        """Start new session or update existing active session."""
        # Check for active session
        active_session_result = await session.execute(
            select(AgentSession).where(
                and_(
                    AgentSession.agent_id == agent_id,
                    AgentSession.session_end.is_(None)
                )
            )
        )
        active_session = active_session_result.scalar_one_or_none()
        
        if not active_session:
            # Create new session
            await self._create_agent_session(session, agent_id, AgentStatus.AVAILABLE, session_type)
    
    async def _end_current_session(
        self,
        session,
        agent_id: uuid.UUID,
        final_status: AgentStatus
    ):
        """End current active session."""
        await session.execute(
            update(AgentSession)
            .where(
                and_(
                    AgentSession.agent_id == agent_id,
                    AgentSession.session_end.is_(None)
                )
            )
            .values(
                session_end=datetime.utcnow(),
                final_status=final_status
            )
        )
    
    def _agent_has_skills(self, agent: Agent, required_skills: List[str]) -> bool:
        """Check if agent has required skills."""
        if not agent.skills or not required_skills:
            return True
        
        agent_skills = set(agent.skills)
        required_skills_set = set(required_skills)
        
        return required_skills_set.issubset(agent_skills)