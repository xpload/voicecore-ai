"""
Call-related database models for VoiceCore AI.

Defines call entities, call status tracking, and call metadata
with comprehensive logging for analytics and compliance.
"""

import enum
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Enum, ForeignKey, JSON, DateTime, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel, TimestampMixin, TenantMixin


class CallStatus(enum.Enum):
    """Call status enumeration for tracking call lifecycle."""
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    TRANSFERRED = "transferred"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    CANCELLED = "cancelled"


class CallDirection(enum.Enum):
    """Call direction enumeration."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallType(enum.Enum):
    """Call type enumeration for categorization."""
    CUSTOMER = "customer"
    SALES = "sales"
    SUPPORT = "support"
    SPAM = "spam"
    INTERNAL = "internal"
    VIP = "vip"
    EMERGENCY = "emergency"


class Call(BaseModel, TimestampMixin, TenantMixin):
    """
    Call model representing individual phone calls in the system.
    
    Tracks complete call lifecycle from initiation to completion
    with comprehensive metadata for analytics and compliance.
    """
    __tablename__ = "calls"
    
    # Twilio integration
    twilio_call_sid = Column(
        String(255),
        unique=True,
        nullable=False,
        doc="Twilio call SID for external reference"
    )
    
    twilio_parent_call_sid = Column(
        String(255),
        nullable=True,
        doc="Parent call SID for transferred calls"
    )
    
    # Call participants
    from_number = Column(
        String(20),
        nullable=False,
        doc="Caller's phone number"
    )
    
    to_number = Column(
        String(20),
        nullable=False,
        doc="Called phone number (tenant's number)"
    )
    
    caller_name = Column(
        String(255),
        nullable=True,
        doc="Caller's name if available"
    )
    
    # Call routing and assignment
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=True,
        doc="Agent handling the call"
    )
    
    department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("department.id"),
        nullable=True,
        doc="Department the call was routed to"
    )
    
    queue_entry_id = Column(
        UUID(as_uuid=True),
        ForeignKey("call_queue.id"),
        nullable=True,
        doc="Reference to queue entry if call is queued"
    )
    
    routing_attempts = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of routing attempts made"
    )
    
    last_routing_attempt = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last routing attempt"
    )
    
    # Call status and timing
    status = Column(
        Enum(CallStatus),
        default=CallStatus.INITIATED,
        nullable=False,
        doc="Current call status"
    )
    
    direction = Column(
        Enum(CallDirection),
        nullable=False,
        doc="Call direction (inbound/outbound)"
    )
    
    call_type = Column(
        Enum(CallType),
        default=CallType.CUSTOMER,
        nullable=False,
        doc="Call type classification"
    )
    
    # Timing information
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the call was answered"
    )
    
    ended_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the call ended"
    )
    
    duration = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Call duration in seconds"
    )
    
    talk_time = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Actual talk time in seconds"
    )
    
    wait_time = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Time spent waiting in queue (seconds)"
    )
    
    # AI interaction tracking
    ai_handled = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether AI handled part of the call"
    )
    
    ai_duration = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Time spent with AI in seconds"
    )
    
    ai_transfer_attempts = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of AI transfer attempts"
    )
    
    ai_resolution_attempted = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether AI attempted to resolve the issue"
    )
    
    # Call quality and metrics
    call_quality_score = Column(
        Float,
        nullable=True,
        doc="Call quality score (1-5)"
    )
    
    customer_satisfaction = Column(
        Integer,
        nullable=True,
        doc="Customer satisfaction rating (1-5)"
    )
    
    # Recording and transcription
    recording_url = Column(
        String(500),
        nullable=True,
        doc="URL to call recording file"
    )
    
    recording_duration = Column(
        Integer,
        nullable=True,
        doc="Recording duration in seconds"
    )
    
    transcript = Column(
        Text,
        nullable=True,
        doc="Full call transcript"
    )
    
    transcript_confidence = Column(
        Float,
        nullable=True,
        doc="Transcript confidence score (0-1)"
    )
    
    # Language and localization
    detected_language = Column(
        String(10),
        nullable=True,
        doc="Detected caller language"
    )
    
    # Spam and security
    spam_score = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Spam probability score (0-1)"
    )
    
    spam_reasons = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Reasons for spam classification"
    )
    
    is_blocked = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the call was blocked"
    )
    
    # VIP and priority handling
    is_vip = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether caller is VIP"
    )
    
    priority_level = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Call priority level (0=normal, higher=more priority)"
    )
    
    # Emotion and sentiment analysis
    emotion_detected = Column(
        String(50),
        nullable=True,
        doc="Detected caller emotion"
    )
    
    sentiment_score = Column(
        Float,
        nullable=True,
        doc="Sentiment score (-1 to 1, negative to positive)"
    )
    
    escalation_triggered = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether automatic escalation was triggered"
    )
    
    # Call outcome and resolution
    resolution_status = Column(
        String(50),
        nullable=True,
        doc="Call resolution status"
    )
    
    resolution_notes = Column(
        Text,
        nullable=True,
        doc="Notes about call resolution"
    )
    
    follow_up_required = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether follow-up is required"
    )
    
    callback_requested = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether caller requested callback"
    )
    
    # Metadata and additional information
    call_metadata = Column(
        "metadata",  # Database column name
        JSON,
        default=dict,
        nullable=False,
        doc="Additional call metadata"
    )
    
    tags = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Call tags for categorization"
    )
    
    # Cost tracking
    cost_cents = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Call cost in cents"
    )
    
    # Relationships
    agent = relationship("Agent")
    department = relationship("Department")
    
    def __repr__(self) -> str:
        return f"<Call(id={self.id}, sid='{self.twilio_call_sid}', status={self.status.value})>"
    
    @property
    def is_active(self) -> bool:
        """Check if call is currently active."""
        active_statuses = [CallStatus.INITIATED, CallStatus.RINGING, CallStatus.IN_PROGRESS, CallStatus.ON_HOLD]
        return self.status in active_statuses
    
    @property
    def is_completed(self) -> bool:
        """Check if call is completed."""
        completed_statuses = [CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.NO_ANSWER, CallStatus.CANCELLED]
        return self.status in completed_statuses
    
    @property
    def total_duration(self) -> Optional[int]:
        """Get total call duration in seconds."""
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return None
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the call."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the call."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def get_metadata(self, key: str, default=None):
        """Get a specific metadata value."""
        return self.metadata.get(key, default) if self.metadata else default
    
    def set_metadata(self, key: str, value) -> None:
        """Set a specific metadata value."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value


class CallEvent(BaseModel, TimestampMixin, TenantMixin):
    """
    Call event tracking for detailed call flow analysis.
    
    Records all significant events during a call lifecycle
    for debugging, analytics, and compliance purposes.
    """
    __tablename__ = "call_events"
    
    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calls.id"),
        nullable=False,
        doc="Reference to the call"
    )
    
    event_type = Column(
        String(50),
        nullable=False,
        doc="Type of event (answered, transferred, hold, etc.)"
    )
    
    event_data = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Event-specific data"
    )
    
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the event occurred"
    )
    
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=True,
        doc="Agent involved in the event"
    )
    
    # Relationships
    call = relationship("Call")
    agent = relationship("Agent")
    
    def __repr__(self) -> str:
        return f"<CallEvent(call_id={self.call_id}, type='{self.event_type}')>"


class CallQueue(BaseModel, TimestampMixin, TenantMixin):
    """
    Call queue management for handling waiting calls.
    
    Tracks calls waiting for available agents with
    priority and timeout management.
    """
    __tablename__ = "call_queue"
    
    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calls.id"),
        nullable=False,
        unique=True,
        doc="Reference to the queued call"
    )
    
    department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("department.id"),
        nullable=False,
        doc="Department queue"
    )
    
    caller_number = Column(
        String(255),
        nullable=False,
        doc="Hashed caller number for privacy"
    )
    
    queue_position = Column(
        Integer,
        nullable=False,
        doc="Position in queue (1 = first)"
    )
    
    priority = Column(
        Integer,
        default=2,
        nullable=False,
        doc="Queue priority (higher = more priority)"
    )
    
    queued_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="When call entered the queue"
    )
    
    assigned_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=True,
        doc="Agent assigned to handle this call"
    )
    
    assigned_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When call was assigned to agent"
    )
    
    estimated_wait_time = Column(
        Integer,
        nullable=True,
        doc="Estimated wait time in seconds"
    )
    
    max_wait_time = Column(
        Integer,
        default=300,
        nullable=False,
        doc="Maximum wait time before timeout"
    )
    
    # Relationships
    call = relationship("Call")
    department = relationship("Department")
    assigned_agent = relationship("Agent")
    
    def __repr__(self) -> str:
        return f"<CallQueue(call_id={self.call_id}, position={self.queue_position})>"
    
    @property
    def wait_time(self) -> int:
        """Get current wait time in seconds."""
        return int((datetime.utcnow() - self.queued_at).total_seconds())
    
    @property
    def is_expired(self) -> bool:
        """Check if call has exceeded maximum wait time."""
        return self.wait_time > self.max_wait_time