"""
Call routing service for VoiceCore AI.

Provides intelligent call routing with extension support, queue management,
and priority handling for the multitenant virtual receptionist system.
"""

import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    Agent, Department, Call, CallQueue, CallStatus, 
    AgentStatus, CallDirection, CallType, VIPCaller, VIPPriority
)
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils
from voicecore.services.vip_service import VIPService


logger = get_logger(__name__)


class RoutingStrategy(Enum):
    """Call routing strategies."""
    ROUND_ROBIN = "round_robin"
    SKILLS_BASED = "skills_based"
    LEAST_BUSY = "least_busy"
    PRIORITY_BASED = "priority_based"
    EXTENSION_DIRECT = "extension_direct"


class CallPriority(Enum):
    """Call priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    VIP = 4
    EMERGENCY = 5


@dataclass
class RoutingResult:
    """Result of call routing operation."""
    success: bool
    target_agent: Optional[Agent] = None
    target_department: Optional[Department] = None
    queue_position: Optional[int] = None
    estimated_wait_time: Optional[int] = None
    routing_reason: str = ""
    error_message: Optional[str] = None


@dataclass
class QueueEntry:
    """Call queue entry."""
    call_id: uuid.UUID
    caller_number: str
    priority: CallPriority
    department_id: uuid.UUID
    queued_at: datetime
    estimated_wait_time: int
    callback_requested: bool = False


class CallRoutingService:
    """
    Intelligent call routing service with extension support and queue management.
    
    Handles call routing decisions, agent availability, queue management,
    and priority-based routing for optimal customer experience.
    """
    
    def __init__(self):
        self.logger = logger
        self.vip_service = VIPService()
    
    async def route_call(
        self,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        caller_number: str,
        requested_extension: Optional[str] = None,
        department_code: Optional[str] = None,
        is_vip: bool = False,
        routing_context: Optional[Dict[str, Any]] = None
    ) -> RoutingResult:
        """
        Route a call to the most appropriate agent or department.
        
        Args:
            tenant_id: Tenant UUID
            call_id: Call UUID
            caller_number: Caller's phone number
            requested_extension: Specific extension requested by caller
            department_code: Department code for routing
            is_vip: Whether caller is VIP
            routing_context: Additional context for routing decisions
            
        Returns:
            RoutingResult: Routing decision and details
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Check if caller is VIP
                vip_caller = None
                if not is_vip:  # Only check if not already identified as VIP
                    vip_caller = await self.vip_service.identify_vip_caller(tenant_id, caller_number)
                    is_vip = vip_caller is not None
                
                # Determine call priority (enhanced with VIP logic)
                priority = self._determine_call_priority(is_vip, routing_context, vip_caller)
                
                # VIP-specific routing logic
                if is_vip and vip_caller:
                    vip_result = await self._handle_vip_routing(
                        session, tenant_id, call_id, vip_caller, priority, caller_number
                    )
                    if vip_result.success or vip_result.queue_position is not None:
                        return vip_result
                
                # Try direct extension routing first
                if requested_extension:
                    result = await self._route_to_extension(
                        session, tenant_id, call_id, requested_extension, priority
                    )
                    if result.success:
                        return result
                
                # Try department-specific routing
                if department_code:
                    result = await self._route_to_department(
                        session, tenant_id, call_id, department_code, priority, caller_number
                    )
                    if result.success or result.queue_position is not None:
                        return result
                
                # Fallback to default department routing
                result = await self._route_to_default_department(
                    session, tenant_id, call_id, priority, caller_number
                )
                
                return result
                
        except Exception as e:
            self.logger.error(
                "Call routing failed",
                tenant_id=str(tenant_id),
                call_id=str(call_id),
                error=str(e)
            )
            return RoutingResult(
                success=False,
                error_message=f"Routing failed: {str(e)}"
            )
    
    async def find_available_agent(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        required_skills: Optional[List[str]] = None,
        exclude_agent_ids: Optional[List[uuid.UUID]] = None
    ) -> Optional[Agent]:
        """
        Find the best available agent based on routing strategy.
        
        Args:
            tenant_id: Tenant UUID
            department_id: Department UUID (optional)
            required_skills: Required agent skills (optional)
            exclude_agent_ids: Agent IDs to exclude (optional)
            
        Returns:
            Optional[Agent]: Best available agent or None
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Build query for available agents
                query = select(Agent).where(
                    and_(
                        Agent.tenant_id == tenant_id,
                        Agent.is_active == True,
                        Agent.status == AgentStatus.AVAILABLE
                    )
                )
                
                # Filter by department if specified
                if department_id:
                    query = query.where(Agent.department_id == department_id)
                
                # Exclude specific agents if specified
                if exclude_agent_ids:
                    query = query.where(~Agent.id.in_(exclude_agent_ids))
                
                # Execute query
                result = await session.execute(query)
                available_agents = result.scalars().all()
                
                if not available_agents:
                    return None
                
                # Filter by required skills if specified
                if required_skills:
                    available_agents = [
                        agent for agent in available_agents
                        if self._agent_has_skills(agent, required_skills)
                    ]
                
                if not available_agents:
                    return None
                
                # Get department routing strategy
                routing_strategy = RoutingStrategy.ROUND_ROBIN
                if department_id:
                    dept_result = await session.execute(
                        select(Department.routing_strategy).where(Department.id == department_id)
                    )
                    dept_strategy = dept_result.scalar_one_or_none()
                    if dept_strategy:
                        routing_strategy = RoutingStrategy(dept_strategy)
                
                # Select agent based on routing strategy
                selected_agent = await self._select_agent_by_strategy(
                    session, available_agents, routing_strategy
                )
                
                return selected_agent
                
        except Exception as e:
            self.logger.error(
                "Failed to find available agent",
                tenant_id=str(tenant_id),
                department_id=str(department_id) if department_id else None,
                error=str(e)
            )
            return None
    
    async def add_to_queue(
        self,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        department_id: uuid.UUID,
        caller_number: str,
        priority: CallPriority = CallPriority.NORMAL
    ) -> Tuple[int, int]:
        """
        Add call to department queue.
        
        Args:
            tenant_id: Tenant UUID
            call_id: Call UUID
            department_id: Department UUID
            caller_number: Caller's phone number
            priority: Call priority
            
        Returns:
            Tuple[int, int]: Queue position and estimated wait time in seconds
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get department queue settings
                dept_result = await session.execute(
                    select(Department).where(Department.id == department_id)
                )
                department = dept_result.scalar_one_or_none()
                
                if not department:
                    raise ValueError(f"Department {department_id} not found")
                
                # Check queue capacity
                current_queue_size = await self._get_queue_size(session, department_id)
                
                if current_queue_size >= department.max_queue_size:
                    raise ValueError("Queue is full")
                
                # Calculate queue position based on priority
                queue_position = await self._calculate_queue_position(
                    session, department_id, priority
                )
                
                # Create queue entry
                queue_entry = CallQueue(
                    tenant_id=tenant_id,
                    call_id=call_id,
                    department_id=department_id,
                    caller_number=SecurityUtils.hash_phone_number(caller_number),
                    priority=priority.value,
                    queue_position=queue_position,
                    queued_at=datetime.utcnow()
                )
                
                session.add(queue_entry)
                
                # Update call status
                await session.execute(
                    "UPDATE calls SET status = :status WHERE id = :call_id",
                    {"status": CallStatus.QUEUED.value, "call_id": call_id}
                )
                
                await session.commit()
                
                # Calculate estimated wait time
                estimated_wait_time = await self._calculate_wait_time(
                    session, department_id, queue_position
                )
                
                self.logger.info(
                    "Call added to queue",
                    tenant_id=str(tenant_id),
                    call_id=str(call_id),
                    department_id=str(department_id),
                    queue_position=queue_position,
                    estimated_wait_time=estimated_wait_time
                )
                
                return queue_position, estimated_wait_time
                
        except Exception as e:
            self.logger.error(
                "Failed to add call to queue",
                tenant_id=str(tenant_id),
                call_id=str(call_id),
                error=str(e)
            )
            raise
    
    async def get_next_queued_call(
        self,
        tenant_id: uuid.UUID,
        department_id: uuid.UUID
    ) -> Optional[CallQueue]:
        """
        Get the next call from the department queue.
        
        Args:
            tenant_id: Tenant UUID
            department_id: Department UUID
            
        Returns:
            Optional[CallQueue]: Next queued call or None
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get highest priority call with lowest queue position
                result = await session.execute(
                    select(CallQueue)
                    .where(
                        and_(
                            CallQueue.tenant_id == tenant_id,
                            CallQueue.department_id == department_id,
                            CallQueue.assigned_agent_id.is_(None)
                        )
                    )
                    .order_by(
                        CallQueue.priority.desc(),
                        CallQueue.queue_position.asc(),
                        CallQueue.queued_at.asc()
                    )
                    .limit(1)
                )
                
                return result.scalar_one_or_none()
                
        except Exception as e:
            self.logger.error(
                "Failed to get next queued call",
                tenant_id=str(tenant_id),
                department_id=str(department_id),
                error=str(e)
            )
            return None
    
    async def assign_queued_call(
        self,
        tenant_id: uuid.UUID,
        queue_entry_id: uuid.UUID,
        agent_id: uuid.UUID
    ) -> bool:
        """
        Assign a queued call to an available agent.
        
        Args:
            tenant_id: Tenant UUID
            queue_entry_id: Queue entry UUID
            agent_id: Agent UUID
            
        Returns:
            bool: True if assignment was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Update queue entry
                await session.execute(
                    """
                    UPDATE call_queue 
                    SET assigned_agent_id = :agent_id, assigned_at = :assigned_at
                    WHERE id = :queue_id AND tenant_id = :tenant_id
                    """,
                    {
                        "agent_id": agent_id,
                        "assigned_at": datetime.utcnow(),
                        "queue_id": queue_entry_id,
                        "tenant_id": tenant_id
                    }
                )
                
                # Update agent status
                await session.execute(
                    "UPDATE agents SET status = :status WHERE id = :agent_id",
                    {"status": AgentStatus.BUSY.value, "agent_id": agent_id}
                )
                
                await session.commit()
                
                self.logger.info(
                    "Queued call assigned to agent",
                    tenant_id=str(tenant_id),
                    queue_entry_id=str(queue_entry_id),
                    agent_id=str(agent_id)
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to assign queued call",
                tenant_id=str(tenant_id),
                queue_entry_id=str(queue_entry_id),
                agent_id=str(agent_id),
                error=str(e)
            )
            return False
    
    async def remove_from_queue(
        self,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        reason: str = "completed"
    ) -> bool:
        """
        Remove call from queue.
        
        Args:
            tenant_id: Tenant UUID
            call_id: Call UUID
            reason: Reason for removal
            
        Returns:
            bool: True if removal was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Remove from queue
                result = await session.execute(
                    """
                    DELETE FROM call_queue 
                    WHERE call_id = :call_id AND tenant_id = :tenant_id
                    """,
                    {"call_id": call_id, "tenant_id": tenant_id}
                )
                
                await session.commit()
                
                if result.rowcount > 0:
                    self.logger.info(
                        "Call removed from queue",
                        tenant_id=str(tenant_id),
                        call_id=str(call_id),
                        reason=reason
                    )
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove call from queue",
                tenant_id=str(tenant_id),
                call_id=str(call_id),
                error=str(e)
            )
            return False
    
    async def get_queue_status(
        self,
        tenant_id: uuid.UUID,
        department_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get current queue status for a department.
        
        Args:
            tenant_id: Tenant UUID
            department_id: Department UUID
            
        Returns:
            Dict[str, Any]: Queue status information
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get queue statistics
                result = await session.execute(
                    """
                    SELECT 
                        COUNT(*) as total_queued,
                        COUNT(CASE WHEN priority >= 4 THEN 1 END) as vip_queued,
                        AVG(EXTRACT(EPOCH FROM (NOW() - queued_at))) as avg_wait_time,
                        MAX(EXTRACT(EPOCH FROM (NOW() - queued_at))) as max_wait_time
                    FROM call_queue 
                    WHERE tenant_id = :tenant_id 
                    AND department_id = :department_id 
                    AND assigned_agent_id IS NULL
                    """,
                    {"tenant_id": tenant_id, "department_id": department_id}
                )
                
                stats = result.fetchone()
                
                # Get available agents count
                agent_result = await session.execute(
                    """
                    SELECT COUNT(*) 
                    FROM agents 
                    WHERE tenant_id = :tenant_id 
                    AND department_id = :department_id 
                    AND is_active = true 
                    AND status = :status
                    """,
                    {
                        "tenant_id": tenant_id,
                        "department_id": department_id,
                        "status": AgentStatus.AVAILABLE.value
                    }
                )
                
                available_agents = agent_result.scalar()
                
                return {
                    "total_queued": stats[0] or 0,
                    "vip_queued": stats[1] or 0,
                    "available_agents": available_agents or 0,
                    "average_wait_time": int(stats[2] or 0),
                    "maximum_wait_time": int(stats[3] or 0),
                    "queue_health": self._calculate_queue_health(
                        stats[0] or 0, available_agents or 0, stats[2] or 0
                    )
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get queue status",
                tenant_id=str(tenant_id),
                department_id=str(department_id),
                error=str(e)
            )
            return {}
    
    # Private helper methods
    
    def _determine_call_priority(
        self, 
        is_vip: bool, 
        routing_context: Optional[Dict[str, Any]],
        vip_caller: Optional[VIPCaller] = None
    ) -> CallPriority:
        """Determine call priority based on caller status and context."""
        if is_vip and vip_caller:
            # Use VIP-specific priority calculation
            if vip_caller.vip_level == VIPPriority.DIAMOND:
                return CallPriority.VIP
            elif vip_caller.vip_level in [VIPPriority.PLATINUM, VIPPriority.GOLD]:
                return CallPriority.HIGH
            else:
                return CallPriority.NORMAL
        elif is_vip:
            return CallPriority.VIP
        
        if routing_context:
            if routing_context.get("is_emergency"):
                return CallPriority.EMERGENCY
            if routing_context.get("is_escalation"):
                return CallPriority.HIGH
        
        return CallPriority.NORMAL
    
    async def _route_to_extension(
        self,
        session,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        extension: str,
        priority: CallPriority
    ) -> RoutingResult:
        """Route call directly to a specific extension."""
        try:
            # Find agent by extension
            result = await session.execute(
                select(Agent).where(
                    and_(
                        Agent.tenant_id == tenant_id,
                        Agent.extension == extension,
                        Agent.is_active == True
                    )
                )
            )
            
            agent = result.scalar_one_or_none()
            
            if not agent:
                return RoutingResult(
                    success=False,
                    routing_reason="extension_not_found",
                    error_message=f"Extension {extension} not found"
                )
            
            if agent.status != AgentStatus.AVAILABLE:
                # Agent is busy, offer callback or queue
                return RoutingResult(
                    success=False,
                    routing_reason="agent_unavailable",
                    error_message=f"Agent at extension {extension} is currently unavailable"
                )
            
            # Update agent status
            agent.status = AgentStatus.BUSY
            
            # Update call assignment
            await session.execute(
                "UPDATE calls SET agent_id = :agent_id, status = :status WHERE id = :call_id",
                {
                    "agent_id": agent.id,
                    "status": CallStatus.CONNECTED.value,
                    "call_id": call_id
                }
            )
            
            await session.commit()
            
            return RoutingResult(
                success=True,
                target_agent=agent,
                routing_reason="direct_extension"
            )
            
        except Exception as e:
            return RoutingResult(
                success=False,
                routing_reason="routing_error",
                error_message=str(e)
            )
    
    async def _route_to_department(
        self,
        session,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        department_code: str,
        priority: CallPriority,
        caller_number: str
    ) -> RoutingResult:
        """Route call to a specific department."""
        try:
            # Find department
            result = await session.execute(
                select(Department).where(
                    and_(
                        Department.tenant_id == tenant_id,
                        Department.code == department_code,
                        Department.is_active == True
                    )
                )
            )
            
            department = result.scalar_one_or_none()
            
            if not department:
                return RoutingResult(
                    success=False,
                    routing_reason="department_not_found",
                    error_message=f"Department {department_code} not found"
                )
            
            # Try to find available agent in department
            agent = await self.find_available_agent(tenant_id, department.id)
            
            if agent:
                # Direct routing to available agent
                agent.status = AgentStatus.BUSY
                
                await session.execute(
                    "UPDATE calls SET agent_id = :agent_id, department_id = :dept_id, status = :status WHERE id = :call_id",
                    {
                        "agent_id": agent.id,
                        "dept_id": department.id,
                        "status": CallStatus.CONNECTED.value,
                        "call_id": call_id
                    }
                )
                
                await session.commit()
                
                return RoutingResult(
                    success=True,
                    target_agent=agent,
                    target_department=department,
                    routing_reason="department_direct"
                )
            else:
                # No available agents, add to queue
                queue_position, wait_time = await self.add_to_queue(
                    tenant_id, call_id, department.id, caller_number, priority
                )
                
                return RoutingResult(
                    success=False,
                    target_department=department,
                    queue_position=queue_position,
                    estimated_wait_time=wait_time,
                    routing_reason="queued_in_department"
                )
                
        except Exception as e:
            return RoutingResult(
                success=False,
                routing_reason="routing_error",
                error_message=str(e)
            )
    
    async def _route_to_default_department(
        self,
        session,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        priority: CallPriority,
        caller_number: str
    ) -> RoutingResult:
        """Route call to default department."""
        try:
            # Find default department
            result = await session.execute(
                select(Department).where(
                    and_(
                        Department.tenant_id == tenant_id,
                        Department.is_default == True,
                        Department.is_active == True
                    )
                )
            )
            
            department = result.scalar_one_or_none()
            
            if not department:
                return RoutingResult(
                    success=False,
                    routing_reason="no_default_department",
                    error_message="No default department configured"
                )
            
            # Try to find available agent
            agent = await self.find_available_agent(tenant_id, department.id)
            
            if agent:
                # Direct routing
                agent.status = AgentStatus.BUSY
                
                await session.execute(
                    "UPDATE calls SET agent_id = :agent_id, department_id = :dept_id, status = :status WHERE id = :call_id",
                    {
                        "agent_id": agent.id,
                        "dept_id": department.id,
                        "status": CallStatus.CONNECTED.value,
                        "call_id": call_id
                    }
                )
                
                await session.commit()
                
                return RoutingResult(
                    success=True,
                    target_agent=agent,
                    target_department=department,
                    routing_reason="default_department_direct"
                )
            else:
                # Add to queue
                queue_position, wait_time = await self.add_to_queue(
                    tenant_id, call_id, department.id, caller_number, priority
                )
                
                return RoutingResult(
                    success=False,
                    target_department=department,
                    queue_position=queue_position,
                    estimated_wait_time=wait_time,
                    routing_reason="queued_in_default_department"
                )
                
        except Exception as e:
            return RoutingResult(
                success=False,
                routing_reason="routing_error",
                error_message=str(e)
            )
    
    def _agent_has_skills(self, agent: Agent, required_skills: List[str]) -> bool:
        """Check if agent has required skills."""
        if not agent.skills or not required_skills:
            return True
        
        agent_skills = set(agent.skills)
        required_skills_set = set(required_skills)
        
        return required_skills_set.issubset(agent_skills)
    
    async def _select_agent_by_strategy(
        self,
        session,
        agents: List[Agent],
        strategy: RoutingStrategy
    ) -> Agent:
        """Select agent based on routing strategy."""
        if strategy == RoutingStrategy.ROUND_ROBIN:
            # Simple round-robin: select agent with least recent assignment
            return min(agents, key=lambda a: a.last_call_at or datetime.min)
        
        elif strategy == RoutingStrategy.LEAST_BUSY:
            # Select agent with lowest current call count
            return min(agents, key=lambda a: a.current_calls or 0)
        
        elif strategy == RoutingStrategy.SKILLS_BASED:
            # For now, return first agent (can be enhanced with skill matching)
            return agents[0]
        
        else:
            # Default to first available agent
            return agents[0]
    
    async def _handle_vip_routing(
        self,
        session,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        vip_caller: VIPCaller,
        priority: CallPriority,
        caller_number: str
    ) -> RoutingResult:
        """Handle VIP-specific routing logic."""
        try:
            from voicecore.models.vip import VIPHandlingRule
            
            # Check for immediate transfer rule
            if vip_caller.has_handling_rule(VIPHandlingRule.IMMEDIATE_TRANSFER):
                if vip_caller.preferred_agent_id:
                    # Try to route to preferred agent immediately
                    agent_result = await session.execute(
                        select(Agent).where(
                            and_(
                                Agent.id == vip_caller.preferred_agent_id,
                                Agent.tenant_id == tenant_id,
                                Agent.is_active == True
                            )
                        )
                    )
                    preferred_agent = agent_result.scalar_one_or_none()
                    
                    if preferred_agent and preferred_agent.status == AgentStatus.AVAILABLE:
                        # Route directly to preferred agent
                        preferred_agent.status = AgentStatus.BUSY
                        
                        await session.execute(
                            "UPDATE calls SET agent_id = :agent_id, status = :status WHERE id = :call_id",
                            {
                                "agent_id": preferred_agent.id,
                                "status": CallStatus.CONNECTED.value,
                                "call_id": call_id
                            }
                        )
                        
                        await session.commit()
                        
                        return RoutingResult(
                            success=True,
                            target_agent=preferred_agent,
                            routing_reason="vip_preferred_agent_immediate"
                        )
            
            # Check for dedicated agent rule
            if vip_caller.has_handling_rule(VIPHandlingRule.DEDICATED_AGENT):
                if vip_caller.preferred_agent_id:
                    # Wait for preferred agent even if busy (add to priority queue)
                    department_id = vip_caller.preferred_department_id
                    if not department_id:
                        # Get agent's department
                        agent_result = await session.execute(
                            select(Agent.department_id).where(Agent.id == vip_caller.preferred_agent_id)
                        )
                        department_id = agent_result.scalar_one_or_none()
                    
                    if department_id:
                        # Add to priority queue with VIP priority
                        queue_position, wait_time = await self.add_to_queue(
                            tenant_id, call_id, department_id, caller_number, priority
                        )
                        
                        return RoutingResult(
                            success=False,
                            queue_position=queue_position,
                            estimated_wait_time=wait_time,
                            routing_reason="vip_dedicated_agent_queue"
                        )
            
            # Check for preferred department routing
            if vip_caller.preferred_department_id:
                # Try to find available agent in preferred department
                agent = await self.find_available_agent(tenant_id, vip_caller.preferred_department_id)
                
                if agent:
                    # Direct routing to preferred department
                    agent.status = AgentStatus.BUSY
                    
                    await session.execute(
                        "UPDATE calls SET agent_id = :agent_id, department_id = :dept_id, status = :status WHERE id = :call_id",
                        {
                            "agent_id": agent.id,
                            "dept_id": vip_caller.preferred_department_id,
                            "status": CallStatus.CONNECTED.value,
                            "call_id": call_id
                        }
                    )
                    
                    await session.commit()
                    
                    return RoutingResult(
                        success=True,
                        target_agent=agent,
                        routing_reason="vip_preferred_department"
                    )
                else:
                    # Add to preferred department queue with VIP priority
                    queue_position, wait_time = await self.add_to_queue(
                        tenant_id, call_id, vip_caller.preferred_department_id, caller_number, priority
                    )
                    
                    return RoutingResult(
                        success=False,
                        queue_position=queue_position,
                        estimated_wait_time=wait_time,
                        routing_reason="vip_preferred_department_queue"
                    )
            
            # If no specific VIP routing rules matched, continue with normal routing
            # but with VIP priority
            return RoutingResult(
                success=False,
                routing_reason="vip_normal_routing_with_priority"
            )
            
        except Exception as e:
            self.logger.error(
                "VIP routing failed",
                tenant_id=str(tenant_id),
                call_id=str(call_id),
                vip_id=str(vip_caller.id),
                error=str(e)
            )
            return RoutingResult(
                success=False,
                routing_reason="vip_routing_error",
                error_message=str(e)
            )
    
    async def _get_queue_size(self, session, department_id: uuid.UUID) -> int:
        """Get current queue size for department."""
        result = await session.execute(
            "SELECT COUNT(*) FROM call_queue WHERE department_id = :dept_id AND assigned_agent_id IS NULL",
            {"dept_id": department_id}
        )
        return result.scalar() or 0
    
    async def _calculate_queue_position(
        self,
        session,
        department_id: uuid.UUID,
        priority: CallPriority
    ) -> int:
        """Calculate queue position based on priority."""
        # Count calls with higher or equal priority
        result = await session.execute(
            """
            SELECT COUNT(*) FROM call_queue 
            WHERE department_id = :dept_id 
            AND priority >= :priority 
            AND assigned_agent_id IS NULL
            """,
            {"dept_id": department_id, "priority": priority.value}
        )
        
        return (result.scalar() or 0) + 1
    
    async def _calculate_wait_time(
        self,
        session,
        department_id: uuid.UUID,
        queue_position: int
    ) -> int:
        """Calculate estimated wait time in seconds."""
        # Get average call duration for the department
        result = await session.execute(
            """
            SELECT AVG(duration) FROM calls 
            WHERE department_id = :dept_id 
            AND duration IS NOT NULL 
            AND created_at >= NOW() - INTERVAL '7 days'
            """,
            {"dept_id": department_id}
        )
        
        avg_duration = result.scalar() or 300  # Default 5 minutes
        
        # Estimate based on queue position and average call duration
        return int(queue_position * avg_duration * 0.8)  # 80% of average duration
    
    def _calculate_queue_health(
        self,
        queued_calls: int,
        available_agents: int,
        avg_wait_time: int
    ) -> str:
        """Calculate queue health status."""
        if available_agents == 0:
            return "critical"
        
        if queued_calls == 0:
            return "excellent"
        
        ratio = queued_calls / available_agents
        
        if ratio > 5 or avg_wait_time > 600:  # More than 5 calls per agent or 10+ min wait
            return "poor"
        elif ratio > 2 or avg_wait_time > 300:  # More than 2 calls per agent or 5+ min wait
            return "fair"
        else:
            return "good"