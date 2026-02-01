"""
Voicemail service for VoiceCore AI.

Provides comprehensive voicemail management including voicemail boxes,
message recording and playback, transcription, and notification system.
"""

import uuid
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    VoicemailBox, VoicemailMessage, VoicemailNotification,
    VoicemailStatus, VoicemailPriority, Tenant, Department, Agent
)
from voicecore.logging import get_logger
from voicecore.config import settings


logger = get_logger(__name__)


@dataclass
class VoicemailBoxSummary:
    """Summary information for a voicemail box."""
    box_id: uuid.UUID
    name: str
    extension: Optional[str]
    department_name: Optional[str]
    agent_name: Optional[str]
    total_messages: int
    unread_messages: int
    is_active: bool
    last_message_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["box_id"] = str(self.box_id)
        if self.last_message_at:
            data["last_message_at"] = self.last_message_at.isoformat()
        return data


@dataclass
class VoicemailMessageSummary:
    """Summary information for a voicemail message."""
    message_id: uuid.UUID
    caller_phone: str
    caller_name: Optional[str]
    duration: int
    status: str
    priority: str
    is_urgent: bool
    received_at: datetime
    listened_at: Optional[datetime]
    has_transcript: bool
    callback_requested: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["message_id"] = str(self.message_id)
        data["received_at"] = self.received_at.isoformat()
        if self.listened_at:
            data["listened_at"] = self.listened_at.isoformat()
        return data
    caller_phone: str
    caller_name: Optional[str]
    duration: int
    status: str
    priority: str
    is_urgent: bool
    received_at: datetime
    listened_at: Optional[datetime]
    has_transcript: bool
    callback_requested: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["message_id"] = str(self.message_id)
        data["received_at"] = self.received_at.isoformat()
        if self.listened_at:
            data["listened_at"] = self.listened_at.isoformat()
        return data


class VoicemailServiceError(Exception):
    """Base exception for voicemail service errors."""
    pass


class VoicemailBoxNotFoundError(VoicemailServiceError):
    """Raised when a voicemail box is not found."""
    pass


class VoicemailMessageNotFoundError(VoicemailServiceError):
    """Raised when a voicemail message is not found."""
    pass


class VoicemailStorageError(VoicemailServiceError):
    """Raised when voicemail storage operations fail."""
    pass


class VoicemailService:
    """
    Comprehensive voicemail management service.
    
    Handles voicemail boxes, message recording and playback,
    transcription, notifications, and cleanup operations.
    """
    
    def __init__(self):
        self.logger = logger
    
    async def create_voicemail_box(
        self,
        tenant_id: uuid.UUID,
        name: str,
        department_id: Optional[uuid.UUID] = None,
        agent_id: Optional[uuid.UUID] = None,
        extension: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> VoicemailBox:
        """
        Create a new voicemail box.
        
        Args:
            tenant_id: Tenant UUID
            name: Voicemail box name
            department_id: Department UUID (for department voicemail)
            agent_id: Agent UUID (for personal voicemail)
            extension: Extension number for direct access
            settings: Additional voicemail box settings
            
        Returns:
            VoicemailBox: Created voicemail box
            
        Raises:
            VoicemailServiceError: If creation fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Create voicemail box
                voicemail_box = VoicemailBox(
                    tenant_id=tenant_id,
                    name=name,
                    department_id=department_id,
                    agent_id=agent_id,
                    extension=extension,
                    settings=settings or {}
                )
                
                # Set default notification email from department or agent
                if department_id:
                    # Get department info for default settings
                    from sqlalchemy import select
                    dept_result = await session.execute(
                        select(Department).where(Department.id == department_id)
                    )
                    department = dept_result.scalar_one_or_none()
                    if department and hasattr(department, 'contact_email'):
                        voicemail_box.notification_email = department.contact_email
                
                elif agent_id:
                    # Get agent info for default settings
                    from sqlalchemy import select
                    agent_result = await session.execute(
                        select(Agent).where(Agent.id == agent_id)
                    )
                    agent = agent_result.scalar_one_or_none()
                    if agent:
                        voicemail_box.notification_email = agent.email
                
                session.add(voicemail_box)
                await session.flush()
                await session.commit()
                
                self.logger.info(
                    "Voicemail box created",
                    tenant_id=str(tenant_id),
                    box_id=str(voicemail_box.id),
                    name=name,
                    department_id=str(department_id) if department_id else None,
                    agent_id=str(agent_id) if agent_id else None
                )
                
                return voicemail_box
                
        except Exception as e:
            self.logger.error("Failed to create voicemail box", error=str(e), tenant_id=str(tenant_id))
            raise VoicemailServiceError(f"Failed to create voicemail box: {str(e)}")
    
    async def get_voicemail_box(
        self,
        tenant_id: uuid.UUID,
        box_id: uuid.UUID
    ) -> Optional[VoicemailBox]:
        """
        Get a voicemail box by ID.
        
        Args:
            tenant_id: Tenant UUID
            box_id: Voicemail box UUID
            
        Returns:
            Optional[VoicemailBox]: Voicemail box or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select
                result = await session.execute(
                    select(VoicemailBox).where(
                        VoicemailBox.id == box_id,
                        VoicemailBox.tenant_id == tenant_id
                    )
                )
                return result.scalar_one_or_none()
                
        except Exception as e:
            self.logger.error("Failed to get voicemail box", error=str(e), tenant_id=str(tenant_id))
            return None
    
    async def list_voicemail_boxes(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        agent_id: Optional[uuid.UUID] = None,
        active_only: bool = True
    ) -> List[VoicemailBoxSummary]:
        """
        List voicemail boxes for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            department_id: Filter by department (optional)
            agent_id: Filter by agent (optional)
            active_only: Only return active boxes
            
        Returns:
            List[VoicemailBoxSummary]: List of voicemail box summaries
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, func, and_
                from sqlalchemy.orm import selectinload
                
                # Build query
                query = select(VoicemailBox).where(VoicemailBox.tenant_id == tenant_id)
                
                if department_id:
                    query = query.where(VoicemailBox.department_id == department_id)
                
                if agent_id:
                    query = query.where(VoicemailBox.agent_id == agent_id)
                
                if active_only:
                    query = query.where(VoicemailBox.is_active == True)
                
                query = query.options(
                    selectinload(VoicemailBox.department),
                    selectinload(VoicemailBox.agent)
                )
                
                result = await session.execute(query)
                boxes = result.scalars().all()
                
                summaries = []
                for box in boxes:
                    # Get last message timestamp
                    last_msg_result = await session.execute(
                        select(func.max(VoicemailMessage.received_at)).where(
                            VoicemailMessage.voicemail_box_id == box.id
                        )
                    )
                    last_message_at = last_msg_result.scalar()
                    
                    summary = VoicemailBoxSummary(
                        box_id=box.id,
                        name=box.name,
                        extension=box.extension,
                        department_name=box.department.name if box.department else None,
                        agent_name=f"{box.agent.first_name} {box.agent.last_name}" if box.agent else None,
                        total_messages=box.total_messages,
                        unread_messages=box.unread_messages,
                        is_active=box.is_active,
                        last_message_at=last_message_at
                    )
                    summaries.append(summary)
                
                return summaries
                
        except Exception as e:
            self.logger.error("Failed to list voicemail boxes", error=str(e), tenant_id=str(tenant_id))
            raise VoicemailServiceError(f"Failed to list voicemail boxes: {str(e)}")
    
    async def record_voicemail_message(
        self,
        tenant_id: uuid.UUID,
        voicemail_box_id: uuid.UUID,
        caller_phone: str,
        audio_url: str,
        duration: int,
        call_id: Optional[uuid.UUID] = None,
        caller_name: Optional[str] = None,
        transcript: Optional[str] = None,
        transcript_confidence: Optional[float] = None
    ) -> VoicemailMessage:
        """
        Record a new voicemail message.
        
        Args:
            tenant_id: Tenant UUID
            voicemail_box_id: Voicemail box UUID
            caller_phone: Caller's phone number
            audio_url: URL to the audio recording
            duration: Message duration in seconds
            call_id: Original call ID (optional)
            caller_name: Caller's name (optional)
            transcript: Message transcript (optional)
            transcript_confidence: Transcript confidence score (optional)
            
        Returns:
            VoicemailMessage: Created voicemail message
            
        Raises:
            VoicemailBoxNotFoundError: If voicemail box not found
            VoicemailServiceError: If recording fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, update
                
                # Verify voicemail box exists
                box_result = await session.execute(
                    select(VoicemailBox).where(
                        VoicemailBox.id == voicemail_box_id,
                        VoicemailBox.tenant_id == tenant_id
                    )
                )
                voicemail_box = box_result.scalar_one_or_none()
                
                if not voicemail_box:
                    raise VoicemailBoxNotFoundError(f"Voicemail box {voicemail_box_id} not found")
                
                # Check if box is at capacity
                if voicemail_box.total_messages >= voicemail_box.max_messages:
                    # Delete oldest message to make room
                    await self._cleanup_old_messages(session, voicemail_box_id, keep_count=voicemail_box.max_messages - 1)
                
                # Create voicemail message
                message = VoicemailMessage(
                    tenant_id=tenant_id,
                    voicemail_box_id=voicemail_box_id,
                    call_id=call_id,
                    caller_phone=caller_phone,
                    caller_name=caller_name,
                    duration=duration,
                    audio_url=audio_url,
                    transcript=transcript,
                    transcript_confidence=transcript_confidence,
                    status=VoicemailStatus.NEW,
                    priority=VoicemailPriority.NORMAL
                )
                
                session.add(message)
                await session.flush()
                
                # Update voicemail box counters
                await session.execute(
                    update(VoicemailBox)
                    .where(VoicemailBox.id == voicemail_box_id)
                    .values(
                        total_messages=VoicemailBox.total_messages + 1,
                        unread_messages=VoicemailBox.unread_messages + 1,
                        updated_at=datetime.utcnow()
                    )
                )
                
                await session.commit()
                
                # Send notifications
                await self._send_voicemail_notification(voicemail_box, message)
                
                self.logger.info(
                    "Voicemail message recorded",
                    tenant_id=str(tenant_id),
                    box_id=str(voicemail_box_id),
                    message_id=str(message.id),
                    caller_phone=caller_phone,
                    duration=duration
                )
                
                return message
                
        except VoicemailBoxNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Failed to record voicemail message", error=str(e), tenant_id=str(tenant_id))
            raise VoicemailServiceError(f"Failed to record voicemail message: {str(e)}")
    
    async def get_voicemail_messages(
        self,
        tenant_id: uuid.UUID,
        voicemail_box_id: uuid.UUID,
        status: Optional[VoicemailStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[VoicemailMessageSummary]:
        """
        Get voicemail messages for a box.
        
        Args:
            tenant_id: Tenant UUID
            voicemail_box_id: Voicemail box UUID
            status: Filter by message status (optional)
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List[VoicemailMessageSummary]: List of voicemail message summaries
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, and_, desc
                
                # Build query
                query = select(VoicemailMessage).where(
                    and_(
                        VoicemailMessage.voicemail_box_id == voicemail_box_id,
                        VoicemailMessage.tenant_id == tenant_id
                    )
                )
                
                if status:
                    query = query.where(VoicemailMessage.status == status)
                
                query = query.order_by(desc(VoicemailMessage.received_at)).limit(limit).offset(offset)
                
                result = await session.execute(query)
                messages = result.scalars().all()
                
                summaries = []
                for msg in messages:
                    summary = VoicemailMessageSummary(
                        message_id=msg.id,
                        caller_phone=msg.caller_phone,
                        caller_name=msg.caller_name,
                        duration=msg.duration,
                        status=msg.status.value,
                        priority=msg.priority.value,
                        is_urgent=msg.is_urgent,
                        received_at=msg.received_at,
                        listened_at=msg.listened_at,
                        has_transcript=bool(msg.transcript),
                        callback_requested=msg.callback_requested
                    )
                    summaries.append(summary)
                
                return summaries
                
        except Exception as e:
            self.logger.error("Failed to get voicemail messages", error=str(e), tenant_id=str(tenant_id))
            raise VoicemailServiceError(f"Failed to get voicemail messages: {str(e)}")
    
    async def mark_message_as_listened(
        self,
        tenant_id: uuid.UUID,
        message_id: uuid.UUID,
        listened_by: uuid.UUID
    ) -> bool:
        """
        Mark a voicemail message as listened.
        
        Args:
            tenant_id: Tenant UUID
            message_id: Voicemail message UUID
            listened_by: Agent UUID who listened to the message
            
        Returns:
            bool: True if marked successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, update
                
                # Get message
                msg_result = await session.execute(
                    select(VoicemailMessage).where(
                        VoicemailMessage.id == message_id,
                        VoicemailMessage.tenant_id == tenant_id
                    )
                )
                message = msg_result.scalar_one_or_none()
                
                if not message:
                    return False
                
                # Update message status if it was new
                was_new = message.status == VoicemailStatus.NEW
                
                await session.execute(
                    update(VoicemailMessage)
                    .where(VoicemailMessage.id == message_id)
                    .values(
                        status=VoicemailStatus.LISTENED,
                        listened_at=datetime.utcnow(),
                        listened_by=listened_by,
                        updated_at=datetime.utcnow()
                    )
                )
                
                # Update voicemail box unread counter if message was new
                if was_new:
                    await session.execute(
                        update(VoicemailBox)
                        .where(VoicemailBox.id == message.voicemail_box_id)
                        .values(
                            unread_messages=VoicemailBox.unread_messages - 1,
                            updated_at=datetime.utcnow()
                        )
                    )
                
                await session.commit()
                
                self.logger.info(
                    "Voicemail message marked as listened",
                    tenant_id=str(tenant_id),
                    message_id=str(message_id),
                    listened_by=str(listened_by)
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to mark message as listened", error=str(e), tenant_id=str(tenant_id))
            return False
    
    async def delete_voicemail_message(
        self,
        tenant_id: uuid.UUID,
        message_id: uuid.UUID
    ) -> bool:
        """
        Delete a voicemail message.
        
        Args:
            tenant_id: Tenant UUID
            message_id: Voicemail message UUID
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, delete, update
                
                # Get message to check status
                msg_result = await session.execute(
                    select(VoicemailMessage).where(
                        VoicemailMessage.id == message_id,
                        VoicemailMessage.tenant_id == tenant_id
                    )
                )
                message = msg_result.scalar_one_or_none()
                
                if not message:
                    return False
                
                was_unread = message.status == VoicemailStatus.NEW
                
                # Delete message
                await session.execute(
                    delete(VoicemailMessage).where(VoicemailMessage.id == message_id)
                )
                
                # Update voicemail box counters
                unread_decrement = 1 if was_unread else 0
                await session.execute(
                    update(VoicemailBox)
                    .where(VoicemailBox.id == message.voicemail_box_id)
                    .values(
                        total_messages=VoicemailBox.total_messages - 1,
                        unread_messages=VoicemailBox.unread_messages - unread_decrement,
                        updated_at=datetime.utcnow()
                    )
                )
                
                await session.commit()
                
                self.logger.info(
                    "Voicemail message deleted",
                    tenant_id=str(tenant_id),
                    message_id=str(message_id)
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to delete voicemail message", error=str(e), tenant_id=str(tenant_id))
            return False
    
    async def _cleanup_old_messages(
        self,
        session,
        voicemail_box_id: uuid.UUID,
        keep_count: int
    ):
        """Clean up old messages to make room for new ones."""
        from sqlalchemy import select, delete, desc
        
        # Get oldest messages to delete
        old_messages_result = await session.execute(
            select(VoicemailMessage.id).where(
                VoicemailMessage.voicemail_box_id == voicemail_box_id
            ).order_by(VoicemailMessage.received_at).limit(100)  # Delete up to 100 old messages
        )
        old_message_ids = [row[0] for row in old_messages_result.fetchall()]
        
        if old_message_ids:
            # Keep only the most recent messages
            if len(old_message_ids) > keep_count:
                messages_to_delete = old_message_ids[:-keep_count] if keep_count > 0 else old_message_ids
                
                await session.execute(
                    delete(VoicemailMessage).where(
                        VoicemailMessage.id.in_(messages_to_delete)
                    )
                )
    
    async def _send_voicemail_notification(
        self,
        voicemail_box: VoicemailBox,
        message: VoicemailMessage
    ):
        """Send notification for new voicemail message."""
        try:
            # Email notification
            if voicemail_box.email_notifications and voicemail_box.notification_email:
                # TODO: Implement email notification
                self.logger.info(
                    "Email notification would be sent",
                    email=voicemail_box.notification_email,
                    message_id=str(message.id)
                )
            
            # SMS notification
            if voicemail_box.sms_notifications and voicemail_box.notification_phone:
                # TODO: Implement SMS notification via Twilio
                self.logger.info(
                    "SMS notification would be sent",
                    phone=voicemail_box.notification_phone,
                    message_id=str(message.id)
                )
                
        except Exception as e:
            self.logger.error("Failed to send voicemail notification", error=str(e))
                
                from sqlalchemy import select
                result = await session.execute(
                    select(VoicemailBox).where(
                        VoicemailBox.id == box_id,
                        VoicemailBox.tenant_id == tenant_id
                    )
                )
                
                return result.scalar_one_or_none()
                
        except Exception as e:
            self.logger.error("Failed to get voicemail box", error=str(e), box_id=str(box_id))
            return None
    
    async def list_voicemail_boxes(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        agent_id: Optional[uuid.UUID] = None,
        active_only: bool = True
    ) -> List[VoicemailBoxSummary]:
        """
        List voicemail boxes for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            department_id: Filter by department (optional)
            agent_id: Filter by agent (optional)
            active_only: Only return active boxes
            
        Returns:
            List[VoicemailBoxSummary]: List of voicemail box summaries
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, func, and_, desc
                from sqlalchemy.orm import selectinload
                
                # Build query
                query = select(VoicemailBox).where(VoicemailBox.tenant_id == tenant_id)
                
                if department_id:
                    query = query.where(VoicemailBox.department_id == department_id)
                
                if agent_id:
                    query = query.where(VoicemailBox.agent_id == agent_id)
                
                if active_only:
                    query = query.where(VoicemailBox.is_active == True)
                
                query = query.options(
                    selectinload(VoicemailBox.department),
                    selectinload(VoicemailBox.agent)
                ).order_by(VoicemailBox.name)
                
                result = await session.execute(query)
                boxes = result.scalars().all()
                
                # Get last message timestamp for each box
                summaries = []
                for box in boxes:
                    # Get last message timestamp
                    last_msg_result = await session.execute(
                        select(func.max(VoicemailMessage.received_at)).where(
                            VoicemailMessage.voicemail_box_id == box.id
                        )
                    )
                    last_message_at = last_msg_result.scalar()
                    
                    summary = VoicemailBoxSummary(
                        box_id=box.id,
                        name=box.name,
                        extension=box.extension,
                        department_name=box.department.name if box.department else None,
                        agent_name=f"{box.agent.first_name} {box.agent.last_name}" if box.agent else None,
                        total_messages=box.total_messages,
                        unread_messages=box.unread_messages,
                        is_active=box.is_active,
                        last_message_at=last_message_at
                    )
                    summaries.append(summary)
                
                return summaries
                
        except Exception as e:
            self.logger.error("Failed to list voicemail boxes", error=str(e), tenant_id=str(tenant_id))
            return []
    
    async def record_voicemail_message(
        self,
        tenant_id: uuid.UUID,
        voicemail_box_id: uuid.UUID,
        caller_phone: str,
        audio_url: str,
        duration: int,
        call_id: Optional[uuid.UUID] = None,
        caller_name: Optional[str] = None,
        priority: VoicemailPriority = VoicemailPriority.NORMAL
    ) -> VoicemailMessage:
        """
        Record a new voicemail message.
        
        Args:
            tenant_id: Tenant UUID
            voicemail_box_id: Voicemail box UUID
            caller_phone: Caller's phone number
            audio_url: URL to the recorded audio
            duration: Message duration in seconds
            call_id: Original call UUID (optional)
            caller_name: Caller's name (optional)
            priority: Message priority
            
        Returns:
            VoicemailMessage: Created voicemail message
            
        Raises:
            VoicemailBoxNotFoundError: If voicemail box doesn't exist
            VoicemailServiceError: If recording fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Verify voicemail box exists
                from sqlalchemy import select, update
                box_result = await session.execute(
                    select(VoicemailBox).where(
                        VoicemailBox.id == voicemail_box_id,
                        VoicemailBox.tenant_id == tenant_id
                    )
                )
                voicemail_box = box_result.scalar_one_or_none()
                
                if not voicemail_box:
                    raise VoicemailBoxNotFoundError(f"Voicemail box {voicemail_box_id} not found")
                
                # Check if box is at capacity
                if voicemail_box.total_messages >= voicemail_box.max_messages:
                    # Delete oldest message to make room
                    await self._cleanup_old_messages(session, voicemail_box_id, keep_count=voicemail_box.max_messages - 1)
                
                # Create voicemail message
                message = VoicemailMessage(
                    tenant_id=tenant_id,
                    voicemail_box_id=voicemail_box_id,
                    call_id=call_id,
                    caller_phone=caller_phone,
                    caller_name=caller_name,
                    duration=duration,
                    audio_url=audio_url,
                    status=VoicemailStatus.NEW,
                    priority=priority,
                    received_at=datetime.utcnow()
                )
                
                session.add(message)
                
                # Update voicemail box counters
                await session.execute(
                    update(VoicemailBox)
                    .where(VoicemailBox.id == voicemail_box_id)
                    .values(
                        total_messages=VoicemailBox.total_messages + 1,
                        unread_messages=VoicemailBox.unread_messages + 1
                    )
                )
                
                await session.flush()
                await session.commit()
                
                self.logger.info(
                    "Voicemail message recorded",
                    tenant_id=str(tenant_id),
                    message_id=str(message.id),
                    box_id=str(voicemail_box_id),
                    caller_phone=caller_phone,
                    duration=duration
                )
                
                # Schedule transcription and notifications
                await self._schedule_transcription(message)
                await self._send_notifications(message, voicemail_box)
                
                return message
                
        except VoicemailBoxNotFoundError:
            raise
        except Exception as e:
            self.logger.error("Failed to record voicemail message", error=str(e))
            raise VoicemailServiceError(f"Failed to record voicemail: {str(e)}")
    
    async def get_voicemail_message(
        self,
        tenant_id: uuid.UUID,
        message_id: uuid.UUID
    ) -> Optional[VoicemailMessage]:
        """
        Get a voicemail message by ID.
        
        Args:
            tenant_id: Tenant UUID
            message_id: Voicemail message UUID
            
        Returns:
            Optional[VoicemailMessage]: Voicemail message or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select
                result = await session.execute(
                    select(VoicemailMessage).where(
                        VoicemailMessage.id == message_id,
                        VoicemailMessage.tenant_id == tenant_id
                    )
                )
                
                return result.scalar_one_or_none()
                
        except Exception as e:
            self.logger.error("Failed to get voicemail message", error=str(e), message_id=str(message_id))
            return None
    
    async def list_voicemail_messages(
        self,
        tenant_id: uuid.UUID,
        voicemail_box_id: uuid.UUID,
        status: Optional[VoicemailStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[VoicemailMessageSummary]:
        """
        List voicemail messages for a voicemail box.
        
        Args:
            tenant_id: Tenant UUID
            voicemail_box_id: Voicemail box UUID
            status: Filter by message status (optional)
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List[VoicemailMessageSummary]: List of voicemail message summaries
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, and_, desc
                
                # Build query
                query = select(VoicemailMessage).where(
                    and_(
                        VoicemailMessage.voicemail_box_id == voicemail_box_id,
                        VoicemailMessage.tenant_id == tenant_id
                    )
                )
                
                if status:
                    query = query.where(VoicemailMessage.status == status)
                
                query = query.order_by(desc(VoicemailMessage.received_at)).limit(limit).offset(offset)
                
                result = await session.execute(query)
                messages = result.scalars().all()
                
                # Convert to summaries
                summaries = []
                for message in messages:
                    summary = VoicemailMessageSummary(
                        message_id=message.id,
                        caller_phone=message.caller_phone,
                        caller_name=message.caller_name,
                        duration=message.duration,
                        status=message.status.value,
                        priority=message.priority.value,
                        is_urgent=message.is_urgent,
                        received_at=message.received_at,
                        listened_at=message.listened_at,
                        has_transcript=bool(message.transcript),
                        callback_requested=message.callback_requested
                    )
                    summaries.append(summary)
                
                return summaries
                
        except Exception as e:
            self.logger.error("Failed to list voicemail messages", error=str(e))
            return []
    
    async def mark_message_as_listened(
        self,
        tenant_id: uuid.UUID,
        message_id: uuid.UUID,
        agent_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        Mark a voicemail message as listened.
        
        Args:
            tenant_id: Tenant UUID
            message_id: Voicemail message UUID
            agent_id: Agent who listened to the message
            
        Returns:
            bool: True if marked successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, update
                
                # Get the message
                result = await session.execute(
                    select(VoicemailMessage).where(
                        VoicemailMessage.id == message_id,
                        VoicemailMessage.tenant_id == tenant_id
                    )
                )
                message = result.scalar_one_or_none()
                
                if not message:
                    return False
                
                # Mark as listened if it was new
                was_new = message.status == VoicemailStatus.NEW
                
                if was_new:
                    await session.execute(
                        update(VoicemailMessage)
                        .where(VoicemailMessage.id == message_id)
                        .values(
                            status=VoicemailStatus.LISTENED,
                            listened_at=datetime.utcnow(),
                            listened_by=agent_id
                        )
                    )
                    
                    # Update voicemail box unread counter
                    await session.execute(
                        update(VoicemailBox)
                        .where(VoicemailBox.id == message.voicemail_box_id)
                        .values(unread_messages=VoicemailBox.unread_messages - 1)
                    )
                
                await session.commit()
                
                self.logger.info(
                    "Voicemail message marked as listened",
                    tenant_id=str(tenant_id),
                    message_id=str(message_id),
                    agent_id=str(agent_id) if agent_id else None
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to mark message as listened", error=str(e))
            return False
    
    async def delete_voicemail_message(
        self,
        tenant_id: uuid.UUID,
        message_id: uuid.UUID
    ) -> bool:
        """
        Delete a voicemail message.
        
        Args:
            tenant_id: Tenant UUID
            message_id: Voicemail message UUID
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, delete, update
                
                # Get the message
                result = await session.execute(
                    select(VoicemailMessage).where(
                        VoicemailMessage.id == message_id,
                        VoicemailMessage.tenant_id == tenant_id
                    )
                )
                message = result.scalar_one_or_none()
                
                if not message:
                    return False
                
                was_unread = message.status == VoicemailStatus.NEW
                voicemail_box_id = message.voicemail_box_id
                
                # Delete the message
                await session.execute(
                    delete(VoicemailMessage).where(VoicemailMessage.id == message_id)
                )
                
                # Update voicemail box counters
                updates = {"total_messages": VoicemailBox.total_messages - 1}
                if was_unread:
                    updates["unread_messages"] = VoicemailBox.unread_messages - 1
                
                await session.execute(
                    update(VoicemailBox)
                    .where(VoicemailBox.id == voicemail_box_id)
                    .values(**updates)
                )
                
                await session.commit()
                
                # TODO: Delete audio file from storage
                await self._delete_audio_file(message.audio_url)
                
                self.logger.info(
                    "Voicemail message deleted",
                    tenant_id=str(tenant_id),
                    message_id=str(message_id)
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to delete voicemail message", error=str(e))
            return False
    
    async def cleanup_old_messages(
        self,
        tenant_id: uuid.UUID,
        days_old: int = 30
    ) -> int:
        """
        Clean up old voicemail messages.
        
        Args:
            tenant_id: Tenant UUID
            days_old: Delete messages older than this many days
            
        Returns:
            int: Number of messages deleted
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, delete, and_
                
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                # Get messages to delete
                result = await session.execute(
                    select(VoicemailMessage).where(
                        and_(
                            VoicemailMessage.tenant_id == tenant_id,
                            VoicemailMessage.received_at < cutoff_date,
                            VoicemailMessage.status != VoicemailStatus.SAVED  # Don't delete saved messages
                        )
                    )
                )
                messages_to_delete = result.scalars().all()
                
                if not messages_to_delete:
                    return 0
                
                # Delete messages and update counters
                deleted_count = 0
                for message in messages_to_delete:
                    await self.delete_voicemail_message(tenant_id, message.id)
                    deleted_count += 1
                
                self.logger.info(
                    "Old voicemail messages cleaned up",
                    tenant_id=str(tenant_id),
                    deleted_count=deleted_count,
                    days_old=days_old
                )
                
                return deleted_count
                
        except Exception as e:
            self.logger.error("Failed to cleanup old messages", error=str(e))
            return 0
    
    # Private helper methods
    
    async def _cleanup_old_messages(
        self,
        session,
        voicemail_box_id: uuid.UUID,
        keep_count: int
    ) -> None:
        """Clean up old messages to make room for new ones."""
        from sqlalchemy import select, delete, desc
        
        # Get oldest messages beyond the keep count
        result = await session.execute(
            select(VoicemailMessage.id).where(
                VoicemailMessage.voicemail_box_id == voicemail_box_id
            ).order_by(desc(VoicemailMessage.received_at)).offset(keep_count)
        )
        
        old_message_ids = [row[0] for row in result]
        
        if old_message_ids:
            await session.execute(
                delete(VoicemailMessage).where(
                    VoicemailMessage.id.in_(old_message_ids)
                )
            )
    
    async def _schedule_transcription(self, message: VoicemailMessage) -> None:
        """Schedule transcription for a voicemail message."""
        # TODO: Integrate with OpenAI Whisper or other transcription service
        # For now, this is a placeholder
        self.logger.info(
            "Transcription scheduled",
            message_id=str(message.id),
            audio_url=message.audio_url
        )
    
    async def _send_notifications(
        self,
        message: VoicemailMessage,
        voicemail_box: VoicemailBox
    ) -> None:
        """Send notifications for a new voicemail message."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(message.tenant_id))
                
                notifications = []
                
                # Email notification
                if voicemail_box.email_notifications and voicemail_box.notification_email:
                    email_notification = VoicemailNotification(
                        tenant_id=message.tenant_id,
                        voicemail_message_id=message.id,
                        notification_type="email",
                        recipient=voicemail_box.notification_email,
                        status="pending"
                    )
                    notifications.append(email_notification)
                
                # SMS notification
                if voicemail_box.sms_notifications and voicemail_box.notification_phone:
                    sms_notification = VoicemailNotification(
                        tenant_id=message.tenant_id,
                        voicemail_message_id=message.id,
                        notification_type="sms",
                        recipient=voicemail_box.notification_phone,
                        status="pending"
                    )
                    notifications.append(sms_notification)
                
                # Save notifications
                for notification in notifications:
                    session.add(notification)
                
                await session.commit()
                
                # TODO: Actually send the notifications
                for notification in notifications:
                    await self._send_notification(notification)
                
        except Exception as e:
            self.logger.error("Failed to send voicemail notifications", error=str(e))
    
    async def _send_notification(self, notification: VoicemailNotification) -> None:
        """Send a single voicemail notification."""
        # TODO: Implement actual notification sending (email, SMS, webhook)
        # For now, just mark as sent
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(notification.tenant_id))
                
                from sqlalchemy import update
                
                await session.execute(
                    update(VoicemailNotification)
                    .where(VoicemailNotification.id == notification.id)
                    .values(
                        status="sent",
                        sent_at=datetime.utcnow()
                    )
                )
                
                await session.commit()
                
                self.logger.info(
                    "Voicemail notification sent",
                    notification_id=str(notification.id),
                    type=notification.notification_type,
                    recipient=notification.recipient
                )
                
        except Exception as e:
            self.logger.error("Failed to send notification", error=str(e))
    
    async def _delete_audio_file(self, audio_url: str) -> None:
        """Delete audio file from storage."""
        # TODO: Implement actual file deletion from storage service
        # This would integrate with AWS S3, Google Cloud Storage, etc.
        self.logger.info("Audio file deletion scheduled", audio_url=audio_url)