"""
Voicemail models for VoiceCore AI.

Defines database models for voicemail messages, voicemail boxes,
and voicemail configuration with proper multitenant isolation.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, 
    ForeignKey, JSON, Float, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from voicecore.models.base import BaseModel


class VoicemailStatus(enum.Enum):
    """Voicemail message status enumeration."""
    NEW = "new"
    LISTENED = "listened"
    SAVED = "saved"
    DELETED = "deleted"
    ARCHIVED = "archived"


class VoicemailPriority(enum.Enum):
    """Voicemail priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class VoicemailBox(BaseModel):
    """
    Voicemail box model for departments and agents.
    
    Represents a voicemail box that can receive and store voicemail messages.
    Each department can have its own voicemail box with custom settings.
    """
    
    __tablename__ = "voicemail_boxes"
    
    # Primary identification
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique voicemail box identifier"
    )
    
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant this voicemail box belongs to"
    )
    
    # Box configuration
    name = Column(
        String(100),
        nullable=False,
        doc="Voicemail box name (e.g., 'Customer Service', 'Sales')"
    )
    
    extension = Column(
        String(10),
        nullable=True,
        doc="Extension number for direct voicemail access"
    )
    
    department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
        doc="Department this voicemail box belongs to"
    )
    
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        doc="Agent this personal voicemail box belongs to"
    )
    
    # Voicemail settings
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this voicemail box is active"
    )
    
    greeting_message = Column(
        Text,
        nullable=True,
        doc="Custom greeting message for this voicemail box"
    )
    
    greeting_audio_url = Column(
        String(500),
        nullable=True,
        doc="URL to custom greeting audio file"
    )
    
    max_message_duration = Column(
        Integer,
        default=300,  # 5 minutes
        nullable=False,
        doc="Maximum message duration in seconds"
    )
    
    max_messages = Column(
        Integer,
        default=100,
        nullable=False,
        doc="Maximum number of messages to store"
    )
    
    # Notification settings
    email_notifications = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether to send email notifications for new voicemails"
    )
    
    notification_email = Column(
        String(255),
        nullable=True,
        doc="Email address for voicemail notifications"
    )
    
    sms_notifications = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether to send SMS notifications for new voicemails"
    )
    
    notification_phone = Column(
        String(20),
        nullable=True,
        doc="Phone number for SMS notifications"
    )
    
    # Auto-delete settings
    auto_delete_after_days = Column(
        Integer,
        default=30,
        nullable=True,
        doc="Automatically delete messages after this many days (null = never)"
    )
    
    # Statistics
    total_messages = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of messages received"
    )
    
    unread_messages = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of unread messages"
    )
    
    # Metadata
    settings = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional voicemail box settings"
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="voicemail_boxes")
    department = relationship("Department", back_populates="voicemail_box")
    agent = relationship("Agent", back_populates="voicemail_box")
    messages = relationship("VoicemailMessage", back_populates="voicemail_box", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<VoicemailBox(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"


class VoicemailMessage(BaseModel):
    """
    Voicemail message model.
    
    Represents an individual voicemail message with audio recording,
    transcription, and metadata.
    """
    
    __tablename__ = "voicemail_messages"
    
    # Primary identification
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique voicemail message identifier"
    )
    
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant this voicemail message belongs to"
    )
    
    voicemail_box_id = Column(
        UUID(as_uuid=True),
        ForeignKey("voicemail_boxes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Voicemail box this message belongs to"
    )
    
    # Call information
    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="SET NULL"),
        nullable=True,
        doc="Original call that generated this voicemail"
    )
    
    caller_phone = Column(
        String(20),
        nullable=False,
        doc="Phone number of the caller"
    )
    
    caller_name = Column(
        String(100),
        nullable=True,
        doc="Name of the caller (if available)"
    )
    
    # Message content
    duration = Column(
        Integer,
        nullable=False,
        doc="Message duration in seconds"
    )
    
    audio_url = Column(
        String(500),
        nullable=False,
        doc="URL to the voicemail audio recording"
    )
    
    audio_format = Column(
        String(10),
        default="mp3",
        nullable=False,
        doc="Audio file format (mp3, wav, etc.)"
    )
    
    file_size = Column(
        Integer,
        nullable=True,
        doc="Audio file size in bytes"
    )
    
    # Transcription
    transcript = Column(
        Text,
        nullable=True,
        doc="Transcribed text of the voicemail message"
    )
    
    transcript_confidence = Column(
        Float,
        nullable=True,
        doc="Confidence score of the transcription (0.0 to 1.0)"
    )
    
    language_detected = Column(
        String(5),
        nullable=True,
        doc="Detected language of the message (e.g., 'en', 'es')"
    )
    
    # Message status and priority
    status = Column(
        SQLEnum(VoicemailStatus),
        default=VoicemailStatus.NEW,
        nullable=False,
        doc="Current status of the voicemail message"
    )
    
    priority = Column(
        SQLEnum(VoicemailPriority),
        default=VoicemailPriority.NORMAL,
        nullable=False,
        doc="Priority level of the message"
    )
    
    is_urgent = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this message is marked as urgent"
    )
    
    # Timestamps
    received_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="When the voicemail was received"
    )
    
    listened_at = Column(
        DateTime,
        nullable=True,
        doc="When the voicemail was first listened to"
    )
    
    listened_by = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        doc="Agent who listened to the message"
    )
    
    # Follow-up information
    callback_requested = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the caller requested a callback"
    )
    
    callback_number = Column(
        String(20),
        nullable=True,
        doc="Phone number for callback (if different from caller_phone)"
    )
    
    callback_completed = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the callback has been completed"
    )
    
    callback_completed_at = Column(
        DateTime,
        nullable=True,
        doc="When the callback was completed"
    )
    
    # Notes and tags
    notes = Column(
        Text,
        nullable=True,
        doc="Notes added by agents about this voicemail"
    )
    
    tags = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Tags associated with this voicemail"
    )
    
    # Metadata
    metadata = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional voicemail message metadata"
    )
    
    # Relationships
    tenant = relationship("Tenant")
    voicemail_box = relationship("VoicemailBox", back_populates="messages")
    call = relationship("Call")
    listened_by_agent = relationship("Agent", foreign_keys=[listened_by])
    
    def __repr__(self) -> str:
        return f"<VoicemailMessage(id={self.id}, caller_phone='{self.caller_phone}', status='{self.status.value}')>"
    
    def mark_as_listened(self, agent_id: Optional[uuid.UUID] = None) -> None:
        """Mark the voicemail as listened."""
        if self.status == VoicemailStatus.NEW:
            self.status = VoicemailStatus.LISTENED
            self.listened_at = datetime.utcnow()
            if agent_id:
                self.listened_by = agent_id
    
    def mark_as_urgent(self) -> None:
        """Mark the voicemail as urgent."""
        self.is_urgent = True
        self.priority = VoicemailPriority.URGENT
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the voicemail."""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the voicemail."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    @property
    def is_new(self) -> bool:
        """Check if the voicemail is new (unlistened)."""
        return self.status == VoicemailStatus.NEW
    
    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string (MM:SS)."""
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes:02d}:{seconds:02d}"


class VoicemailNotification(BaseModel):
    """
    Voicemail notification model.
    
    Tracks notifications sent for voicemail messages to ensure
    proper delivery and avoid duplicate notifications.
    """
    
    __tablename__ = "voicemail_notifications"
    
    # Primary identification
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique notification identifier"
    )
    
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant this notification belongs to"
    )
    
    voicemail_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("voicemail_messages.id", ondelete="CASCADE"),
        nullable=False,
        doc="Voicemail message this notification is for"
    )
    
    # Notification details
    notification_type = Column(
        String(20),
        nullable=False,
        doc="Type of notification (email, sms, webhook)"
    )
    
    recipient = Column(
        String(255),
        nullable=False,
        doc="Notification recipient (email address, phone number, etc.)"
    )
    
    status = Column(
        String(20),
        default="pending",
        nullable=False,
        doc="Notification status (pending, sent, failed, delivered)"
    )
    
    sent_at = Column(
        DateTime,
        nullable=True,
        doc="When the notification was sent"
    )
    
    delivered_at = Column(
        DateTime,
        nullable=True,
        doc="When the notification was delivered (if available)"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if notification failed"
    )
    
    retry_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retry attempts"
    )
    
    max_retries = Column(
        Integer,
        default=3,
        nullable=False,
        doc="Maximum number of retry attempts"
    )
    
    # Metadata
    metadata = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional notification metadata"
    )
    
    # Relationships
    tenant = relationship("Tenant")
    voicemail_message = relationship("VoicemailMessage")
    
    def __repr__(self) -> str:
        return f"<VoicemailNotification(id={self.id}, type='{self.notification_type}', status='{self.status}')>"
    
    def mark_as_sent(self) -> None:
        """Mark the notification as sent."""
        self.status = "sent"
        self.sent_at = datetime.utcnow()
    
    def mark_as_delivered(self) -> None:
        """Mark the notification as delivered."""
        self.status = "delivered"
        self.delivered_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str) -> None:
        """Mark the notification as failed."""
        self.status = "failed"
        self.error_message = error_message
        self.retry_count += 1
    
    @property
    def can_retry(self) -> bool:
        """Check if the notification can be retried."""
        return self.retry_count < self.max_retries and self.status == "failed"