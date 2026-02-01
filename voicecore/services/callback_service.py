"""
Callback request service for VoiceCore AI.

Provides comprehensive callback request management including scheduling,
automated execution, and status tracking for the multitenant system.
"""

import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    CallbackRequest, CallbackSchedule, CallbackAttempt, Call,
    CallbackStatus, CallbackPriority, CallbackType, Agent, Department
)
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils


logger = get_logger(__name__)


class CallbackServiceError(Exception):
    """Base exception for callback service errors."""
    pass


class CallbackNotFoundError(CallbackServiceError):
    """Raised when a callback request is not found."""
    pass


class CallbackSchedulingError(CallbackServiceError):
    """Raised when callback scheduling fails."""
    pass


class CallbackService:
    """
    Comprehensive callback request management service.
    
    Handles callback request creation, scheduling, automated execution,
    and status tracking for optimal customer service experience.
    """
    
    def __init__(self):
        self.logger = logger
    
    async def create_callback_request(
        self,
        tenant_id: uuid.UUID,
        callback_data: Dict[str, Any]
    ) -> CallbackRequest:
        """
        Create a new callback request.
        
        Args:
            tenant_id: Tenant UUID
            callback_data: Dictionary containing callback request information
            
        Returns:
            CallbackRequest: Created callback request instance
            
        Raises:
            CallbackServiceError: If creation fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Hash phone number for privacy
                hashed_phone = SecurityUtils.hash_phone_number(callback_data["caller_number"])
                
                # Create callback request
                callback_request = CallbackRequest(
                    tenant_id=tenant_id,
                    original_call_id=callback_data.get("original_call_id"),
                    caller_number=hashed_phone,
                    caller_name=callback_data.get("caller_name"),
                    caller_email=callback_data.get("caller_email"),
                    callback_reason=callback_data.get("callback_reason"),
                    callback_type=CallbackType(callback_data.get("callback_type", CallbackType.GENERAL.value)),
                    priority=CallbackPriority(callback_data.get("priority", CallbackPriority.NORMAL.value)),
                    requested_time=callback_data.get("requested_time"),
                    time_window_start=callback_data.get("time_window_start"),
                    time_window_end=callback_data.get("time_window_end"),
                    timezone=callback_data.get("timezone", "UTC"),
                    department_id=callback_data.get("department_id"),
                    preferred_agent_id=callback_data.get("preferred_agent_id"),
                    max_attempts=callback_data.get("max_attempts", 3),
                    sms_notifications=callback_data.get("sms_notifications", False),
                    email_notifications=callback_data.get("email_notifications", False),
                    tags=callback_data.get("tags", []),
                    metadata=callback_data.get("metadata", {})
                )
                
                session.add(callback_request)
                await session.flush()  # Get the ID
                
                # Auto-schedule if requested time is provided
                if callback_request.requested_time:
                    await self._schedule_callback(session, callback_request)
                
                await session.commit()
                
                self.logger.info(
                    "Callback request created",
                    tenant_id=str(tenant_id),
                    callback_id=str(callback_request.id),
                    caller_name=callback_request.caller_name,
                    callback_type=callback_request.callback_type.value
                )
                
                return callback_request
                
        except Exception as e:
            self.logger.error("Callback request creation failed", tenant_id=str(tenant_id), error=str(e))
            raise CallbackServiceError(f"Failed to create callback request: {str(e)}")
    
    async def get_callback_request(
        self,
        tenant_id: uuid.UUID,
        callback_id: uuid.UUID
    ) -> Optional[CallbackRequest]:
        """
        Get callback request by ID.
        
        Args:
            tenant_id: Tenant UUID
            callback_id: Callback request UUID
            
        Returns:
            Optional[CallbackRequest]: Callback request instance or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(CallbackRequest)
                    .options(
                        selectinload(CallbackRequest.assigned_agent),
                        selectinload(CallbackRequest.department),
                        selectinload(CallbackRequest.original_call)
                    )
                    .where(
                        and_(
                            CallbackRequest.tenant_id == tenant_id,
                            CallbackRequest.id == callback_id
                        )
                    )
                )
                
                return result.scalar_one_or_none()
                
        except Exception as e:
            self.logger.error(
                "Failed to get callback request",
                tenant_id=str(tenant_id),
                callback_id=str(callback_id),
                error=str(e)
            )
            return None
    
    async def list_callback_requests(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[CallbackStatus] = None,
        priority: Optional[CallbackPriority] = None,
        callback_type: Optional[CallbackType] = None,
        department_id: Optional[uuid.UUID] = None,
        agent_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None
    ) -> List[CallbackRequest]:
        """
        List callback requests with filtering and pagination.
        
        Args:
            tenant_id: Tenant UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by callback status
            priority: Filter by callback priority
            callback_type: Filter by callback type
            department_id: Filter by department
            agent_id: Filter by assigned agent
            search: Search term for caller name or reason
            
        Returns:
            List[CallbackRequest]: List of callback request instances
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                query = select(CallbackRequest).where(CallbackRequest.tenant_id == tenant_id)
                
                # Apply filters
                if status:
                    query = query.where(CallbackRequest.status == status)
                
                if priority:
                    query = query.where(CallbackRequest.priority == priority)
                
                if callback_type:
                    query = query.where(CallbackRequest.callback_type == callback_type)
                
                if department_id:
                    query = query.where(CallbackRequest.department_id == department_id)
                
                if agent_id:
                    query = query.where(CallbackRequest.assigned_agent_id == agent_id)
                
                if search:
                    search_term = f"%{search}%"
                    query = query.where(
                        or_(
                            CallbackRequest.caller_name.ilike(search_term),
                            CallbackRequest.callback_reason.ilike(search_term)
                        )
                    )
                
                # Apply pagination and ordering
                query = query.offset(skip).limit(limit).order_by(
                    CallbackRequest.priority.desc(),
                    CallbackRequest.scheduled_time.asc(),
                    CallbackRequest.created_at.asc()
                )
                
                result = await session.execute(query)
                return list(result.scalars().all())
                
        except Exception as e:
            self.logger.error("Failed to list callback requests", tenant_id=str(tenant_id), error=str(e))
            return []
    
    async def schedule_callback(
        self,
        tenant_id: uuid.UUID,
        callback_id: uuid.UUID,
        scheduled_time: datetime,
        agent_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        Schedule a callback request for a specific time.
        
        Args:
            tenant_id: Tenant UUID
            callback_id: Callback request UUID
            scheduled_time: When to schedule the callback
            agent_id: Specific agent to assign (optional)
            
        Returns:
            bool: True if scheduling was successful
            
        Raises:
            CallbackNotFoundError: If callback request doesn't exist
            CallbackSchedulingError: If scheduling fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get callback request
                result = await session.execute(
                    select(CallbackRequest).where(
                        and_(
                            CallbackRequest.tenant_id == tenant_id,
                            CallbackRequest.id == callback_id
                        )
                    )
                )
                callback_request = result.scalar_one_or_none()
                
                if not callback_request:
                    raise CallbackNotFoundError(f"Callback request {callback_id} not found")
                
                # Validate scheduling time
                if scheduled_time <= datetime.utcnow():
                    raise CallbackSchedulingError("Cannot schedule callback in the past")
                
                # Check if time is within acceptable window
                if callback_request.time_window_start and scheduled_time < callback_request.time_window_start:
                    raise CallbackSchedulingError("Scheduled time is before acceptable window")
                
                if callback_request.time_window_end and scheduled_time > callback_request.time_window_end:
                    raise CallbackSchedulingError("Scheduled time is after acceptable window")
                
                # Find available agent if not specified
                if not agent_id:
                    agent_id = await self._find_available_agent(
                        session, tenant_id, callback_request.department_id, scheduled_time
                    )
                
                # Update callback request
                callback_request.scheduled_time = scheduled_time
                callback_request.assigned_agent_id = agent_id
                callback_request.status = CallbackStatus.SCHEDULED
                
                await session.commit()
                
                self.logger.info(
                    "Callback scheduled",
                    tenant_id=str(tenant_id),
                    callback_id=str(callback_id),
                    scheduled_time=scheduled_time.isoformat(),
                    agent_id=str(agent_id) if agent_id else None
                )
                
                return True
                
        except (CallbackNotFoundError, CallbackSchedulingError):
            raise
        except Exception as e:
            self.logger.error(
                "Callback scheduling failed",
                tenant_id=str(tenant_id),
                callback_id=str(callback_id),
                error=str(e)
            )
            raise CallbackSchedulingError(f"Failed to schedule callback: {str(e)}")
    
    async def execute_callback(
        self,
        tenant_id: uuid.UUID,
        callback_id: uuid.UUID,
        agent_id: uuid.UUID
    ) -> CallbackAttempt:
        """
        Execute a callback attempt.
        
        Args:
            tenant_id: Tenant UUID
            callback_id: Callback request UUID
            agent_id: Agent making the callback
            
        Returns:
            CallbackAttempt: Created callback attempt record
            
        Raises:
            CallbackNotFoundError: If callback request doesn't exist
            CallbackServiceError: If execution fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get callback request
                result = await session.execute(
                    select(CallbackRequest).where(
                        and_(
                            CallbackRequest.tenant_id == tenant_id,
                            CallbackRequest.id == callback_id
                        )
                    )
                )
                callback_request = result.scalar_one_or_none()
                
                if not callback_request:
                    raise CallbackNotFoundError(f"Callback request {callback_id} not found")
                
                # Update callback status
                callback_request.status = CallbackStatus.IN_PROGRESS
                callback_request.assigned_agent_id = agent_id
                
                # Create attempt record
                attempt = CallbackAttempt(
                    tenant_id=tenant_id,
                    callback_request_id=callback_id,
                    attempt_number=callback_request.attempts + 1,
                    attempted_by_agent_id=agent_id,
                    outcome="initiated"
                )
                
                session.add(attempt)
                await session.commit()
                
                self.logger.info(
                    "Callback execution started",
                    tenant_id=str(tenant_id),
                    callback_id=str(callback_id),
                    agent_id=str(agent_id),
                    attempt_number=attempt.attempt_number
                )
                
                return attempt
                
        except CallbackNotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                "Callback execution failed",
                tenant_id=str(tenant_id),
                callback_id=str(callback_id),
                error=str(e)
            )
            raise CallbackServiceError(f"Failed to execute callback: {str(e)}")
    
    async def complete_callback_attempt(
        self,
        tenant_id: uuid.UUID,
        attempt_id: uuid.UUID,
        outcome: str,
        call_id: Optional[uuid.UUID] = None,
        duration_seconds: Optional[int] = None,
        caller_reached: bool = False,
        issue_resolved: Optional[bool] = None,
        agent_notes: Optional[str] = None,
        caller_feedback: Optional[str] = None
    ) -> bool:
        """
        Complete a callback attempt with results.
        
        Args:
            tenant_id: Tenant UUID
            attempt_id: Callback attempt UUID
            outcome: Attempt outcome
            call_id: Reference to actual call if connected
            duration_seconds: Call duration if connected
            caller_reached: Whether caller was reached
            issue_resolved: Whether issue was resolved
            agent_notes: Agent notes
            caller_feedback: Caller feedback
            
        Returns:
            bool: True if completion was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get attempt and callback request
                result = await session.execute(
                    select(CallbackAttempt)
                    .options(selectinload(CallbackAttempt.callback_request))
                    .where(
                        and_(
                            CallbackAttempt.tenant_id == tenant_id,
                            CallbackAttempt.id == attempt_id
                        )
                    )
                )
                attempt = result.scalar_one_or_none()
                
                if not attempt:
                    return False
                
                callback_request = attempt.callback_request
                
                # Update attempt
                attempt.outcome = outcome
                attempt.call_id = call_id
                attempt.duration_seconds = duration_seconds
                attempt.caller_reached = caller_reached
                attempt.issue_resolved = issue_resolved
                attempt.agent_notes = agent_notes
                attempt.caller_feedback = caller_feedback
                
                # Update callback request
                callback_request.update_attempt(outcome, agent_notes)
                
                # Determine final status
                if caller_reached and issue_resolved:
                    callback_request.status = CallbackStatus.COMPLETED
                    callback_request.completed_at = datetime.utcnow()
                    callback_request.completion_call_id = call_id
                    callback_request.duration_seconds = duration_seconds
                    callback_request.resolution_achieved = issue_resolved
                elif not callback_request.can_retry:
                    callback_request.status = CallbackStatus.FAILED
                else:
                    callback_request.status = CallbackStatus.PENDING
                
                await session.commit()
                
                self.logger.info(
                    "Callback attempt completed",
                    tenant_id=str(tenant_id),
                    attempt_id=str(attempt_id),
                    outcome=outcome,
                    caller_reached=caller_reached,
                    final_status=callback_request.status.value
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to complete callback attempt",
                tenant_id=str(tenant_id),
                attempt_id=str(attempt_id),
                error=str(e)
            )
            return False
    
    async def get_pending_callbacks(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        agent_id: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> List[CallbackRequest]:
        """
        Get pending callbacks ready for execution.
        
        Args:
            tenant_id: Tenant UUID
            department_id: Filter by department (optional)
            agent_id: Filter by assigned agent (optional)
            limit: Maximum number of callbacks to return
            
        Returns:
            List[CallbackRequest]: List of pending callback requests
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                current_time = datetime.utcnow()
                
                query = select(CallbackRequest).where(
                    and_(
                        CallbackRequest.tenant_id == tenant_id,
                        or_(
                            CallbackRequest.status == CallbackStatus.SCHEDULED,
                            and_(
                                CallbackRequest.status == CallbackStatus.PENDING,
                                CallbackRequest.next_attempt_at <= current_time
                            )
                        ),
                        or_(
                            CallbackRequest.scheduled_time <= current_time,
                            CallbackRequest.next_attempt_at <= current_time
                        )
                    )
                )
                
                if department_id:
                    query = query.where(CallbackRequest.department_id == department_id)
                
                if agent_id:
                    query = query.where(CallbackRequest.assigned_agent_id == agent_id)
                
                # Order by priority and scheduled time
                query = query.order_by(
                    CallbackRequest.priority.desc(),
                    CallbackRequest.scheduled_time.asc()
                ).limit(limit)
                
                result = await session.execute(query)
                return list(result.scalars().all())
                
        except Exception as e:
            self.logger.error("Failed to get pending callbacks", tenant_id=str(tenant_id), error=str(e))
            return []
    
    async def cancel_callback(
        self,
        tenant_id: uuid.UUID,
        callback_id: uuid.UUID,
        reason: str = "cancelled_by_user"
    ) -> bool:
        """
        Cancel a callback request.
        
        Args:
            tenant_id: Tenant UUID
            callback_id: Callback request UUID
            reason: Cancellation reason
            
        Returns:
            bool: True if cancellation was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    update(CallbackRequest)
                    .where(
                        and_(
                            CallbackRequest.tenant_id == tenant_id,
                            CallbackRequest.id == callback_id,
                            CallbackRequest.status.in_([
                                CallbackStatus.PENDING,
                                CallbackStatus.SCHEDULED
                            ])
                        )
                    )
                    .values(
                        status=CallbackStatus.CANCELLED,
                        system_notes=func.concat(
                            func.coalesce(CallbackRequest.system_notes, ''),
                            f"\n{datetime.utcnow().isoformat()}: Cancelled - {reason}"
                        )
                    )
                )
                
                await session.commit()
                
                if result.rowcount > 0:
                    self.logger.info(
                        "Callback cancelled",
                        tenant_id=str(tenant_id),
                        callback_id=str(callback_id),
                        reason=reason
                    )
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to cancel callback",
                tenant_id=str(tenant_id),
                callback_id=str(callback_id),
                error=str(e)
            )
            return False
    
    async def get_callback_analytics(
        self,
        tenant_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        department_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Get callback analytics and metrics.
        
        Args:
            tenant_id: Tenant UUID
            start_date: Start date for analytics period
            end_date: End date for analytics period
            department_id: Filter by department (optional)
            
        Returns:
            Dict[str, Any]: Callback analytics data
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Set default date range if not provided
                if not end_date:
                    end_date = datetime.utcnow()
                if not start_date:
                    start_date = end_date - timedelta(days=30)
                
                analytics = {}
                
                # Base query conditions
                conditions = [
                    CallbackRequest.tenant_id == tenant_id,
                    CallbackRequest.created_at >= start_date,
                    CallbackRequest.created_at <= end_date
                ]
                
                if department_id:
                    conditions.append(CallbackRequest.department_id == department_id)
                
                # Get callback volume by status
                status_stats = await session.execute(
                    select(
                        CallbackRequest.status,
                        func.count().label('count')
                    )
                    .where(and_(*conditions))
                    .group_by(CallbackRequest.status)
                )
                
                analytics['by_status'] = {
                    row[0].value: row[1] for row in status_stats.fetchall()
                }
                
                # Get success metrics
                success_stats = await session.execute(
                    select(
                        func.count().label('total_callbacks'),
                        func.sum(func.cast(CallbackRequest.resolution_achieved, Integer)).label('resolved_callbacks'),
                        func.avg(CallbackRequest.attempts).label('avg_attempts'),
                        func.avg(CallbackRequest.duration_seconds).label('avg_duration')
                    )
                    .where(and_(*conditions))
                )
                
                success_row = success_stats.fetchone()
                if success_row:
                    total = success_row[0] or 0
                    resolved = success_row[1] or 0
                    analytics['total_callbacks'] = total
                    analytics['resolved_callbacks'] = resolved
                    analytics['success_rate'] = (resolved / total * 100) if total > 0 else 0
                    analytics['avg_attempts'] = float(success_row[2]) if success_row[2] else 0
                    analytics['avg_duration'] = float(success_row[3]) if success_row[3] else 0
                
                # Get callback volume by type
                type_stats = await session.execute(
                    select(
                        CallbackRequest.callback_type,
                        func.count().label('count')
                    )
                    .where(and_(*conditions))
                    .group_by(CallbackRequest.callback_type)
                )
                
                analytics['by_type'] = {
                    row[0].value: row[1] for row in type_stats.fetchall()
                }
                
                return analytics
                
        except Exception as e:
            self.logger.error(
                "Failed to get callback analytics",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {}
    
    # Private helper methods
    
    async def _schedule_callback(self, session, callback_request: CallbackRequest):
        """Schedule a callback request automatically."""
        try:
            # Find appropriate schedule
            schedule = await self._find_callback_schedule(
                session, callback_request.department_id, callback_request.assigned_agent_id
            )
            
            if not schedule:
                # Use default scheduling
                callback_request.scheduled_time = callback_request.requested_time
                return
            
            # Find next available slot
            available_time = schedule.get_next_available_slot(
                callback_request.requested_time or datetime.utcnow()
            )
            
            if available_time:
                callback_request.scheduled_time = available_time
                callback_request.status = CallbackStatus.SCHEDULED
            
        except Exception as e:
            self.logger.warning("Auto-scheduling failed", error=str(e))
    
    async def _find_callback_schedule(
        self,
        session,
        department_id: Optional[uuid.UUID],
        agent_id: Optional[uuid.UUID]
    ) -> Optional[CallbackSchedule]:
        """Find appropriate callback schedule."""
        try:
            # Try agent-specific schedule first
            if agent_id:
                result = await session.execute(
                    select(CallbackSchedule).where(
                        and_(
                            CallbackSchedule.agent_id == agent_id,
                            CallbackSchedule.is_active == True
                        )
                    ).order_by(CallbackSchedule.priority.desc())
                )
                schedule = result.scalar_one_or_none()
                if schedule:
                    return schedule
            
            # Try department schedule
            if department_id:
                result = await session.execute(
                    select(CallbackSchedule).where(
                        and_(
                            CallbackSchedule.department_id == department_id,
                            CallbackSchedule.is_active == True
                        )
                    ).order_by(CallbackSchedule.priority.desc())
                )
                schedule = result.scalar_one_or_none()
                if schedule:
                    return schedule
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to find callback schedule", error=str(e))
            return None
    
    async def _find_available_agent(
        self,
        session,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID],
        scheduled_time: datetime
    ) -> Optional[uuid.UUID]:
        """Find available agent for callback at scheduled time."""
        try:
            # For now, just find any available agent in the department
            # In a real implementation, this would check agent schedules and availability
            
            query = select(Agent.id).where(
                and_(
                    Agent.tenant_id == tenant_id,
                    Agent.is_active == True
                )
            )
            
            if department_id:
                query = query.where(Agent.department_id == department_id)
            
            result = await session.execute(query.limit(1))
            agent_id = result.scalar_one_or_none()
            
            return agent_id
            
        except Exception as e:
            self.logger.error("Failed to find available agent", error=str(e))
            return None