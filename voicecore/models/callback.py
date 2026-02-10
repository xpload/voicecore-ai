"""
Callback request models for VoiceCore AI.

Defines callback request entities, scheduling, and status tracking
for automated callback management in the multitenant system.
"""

import enum
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, Boolean, Enum, ForeignKey, JSON, DateTime, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel, TimestampMixin, TenantMixin


class CallbackStatus(enum.Enum):
    """Callback request status enumeration."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CallbackPriority(enum.Enum):
    """Callback priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    VIP = 5


class CallbackType(enum.Enum):
    """Callback request types."""
    GENERAL = "general"
    SALES = "sales"
    SUPPORT = "support"
    TECHNICAL = "technical"
    BILLING = "billing"
    COMPLAINT = "complaint"
    FOLLOW_UP = "follow_up"


class CallbackRequest(BaseModel, TimestampMixin, TenantMixin):
    __tablename__ = "callback_request"
    """
    Callback request model for managing return call requests.
    
    Tracks callback requests from callers who prefer to be called back
    rather than waiting in queue, with scheduling and priority management.
    """
    
    # Original call reference
    original_call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("call.id"),
        nullable=True,
        doc="Reference to original call that triggered callback request"
    )
    
    # Caller information
    caller_number = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Hashed caller phone number for privacy"
    )
    
    caller_name = Column(
        String(255),
        nullable=True,
        doc="Caller's name if provided"
    )
    
    caller_email = Column(
        String(255),
        nullable=True,
        doc="Caller's email for notifications"
    )
    
    # Callback details
    callback_reason = Column(
        Text,
        nullable=True,
        doc="Reason for callback request"
    )
    
    callback_type = Column(
        Enum(CallbackType),
        default=CallbackType.GENERAL,
        nullable=False,
        doc="Type of callback request"
    )
    
    priority = Column(
        Enum(CallbackPriority),
        default=CallbackPriority.NORMAL,
        nullable=False,
        doc="Callback priority level"
    )
    
    # Scheduling
    requested_time = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Caller's preferred callback time"
    )
    
    scheduled_time = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Actual scheduled callback time"
    )
    
    time_window_start = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Start of acceptable callback time window"
    )
    
    time_window_end = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="End of acceptable callback time window"
    )
    
    timezone = Column(
        String(50),
        nullable=True,
        doc="Caller's timezone for scheduling"
    )
    
    # Assignment and routing
    assigned_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=True,
        doc="Agent assigned to handle callback"
    )
    
    department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("department.id"),
        nullable=True,
        doc="Department responsible for callback"
    )
    
    preferred_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=True,
        doc="Caller's preferred agent if any"
    )
    
    # Status and tracking
    status = Column(
        Enum(CallbackStatus),
        default=CallbackStatus.PENDING,
        nullable=False,
        doc="Current callback status"
    )
    
    attempts = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of callback attempts made"
    )
    
    max_attempts = Column(
        Integer,
        default=3,
        nullable=False,
        doc="Maximum number of callback attempts"
    )
    
    last_attempt_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last callback attempt"
    )
    
    next_attempt_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp for next callback attempt"
    )
    
    # Completion tracking
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When callback was completed"
    )
    
    completion_call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("call.id"),
        nullable=True,
        doc="Reference to successful callback call"
    )
    
    duration_seconds = Column(
        Integer,
        nullable=True,
        doc="Duration of successful callback in seconds"
    )
    
    # Outcome and feedback
    outcome = Column(
        String(100),
        nullable=True,
        doc="Callback outcome (connected, no_answer, busy, etc.)"
    )
    
    caller_satisfaction = Column(
        Integer,
        nullable=True,
        doc="Caller satisfaction rating (1-5)"
    )
    
    resolution_achieved = Column(
        Boolean,
        nullable=True,
        doc="Whether the caller's issue was resolved"
    )
    
    follow_up_required = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether additional follow-up is needed"
    )
    
    # Notes and metadata
    agent_notes = Column(
        Text,
        nullable=True,
        doc="Notes from assigned agent"
    )
    
    system_notes = Column(
        Text,
        nullable=True,
        doc="System-generated notes and logs"
    )
    
    tags = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Tags for categorization"
    )
    
    callback_metadata = Column("metadata", 
        JSON,
        default=dict,
        nullable=False,
        doc="Additional callback metadata"
    )
    
    # Notification settings
    sms_notifications = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether to send SMS notifications"
    )
    
    email_notifications = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether to send email notifications"
    )
    
    notification_sent = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether notification was sent to caller"
    )
    
    # Relationships
    original_call = relationship("Call", foreign_keys=[original_call_id])
    completion_call = relationship("Call", foreign_keys=[completion_call_id])
    assigned_agent = relationship("Agent", foreign_keys=[assigned_agent_id])
    preferred_agent = relationship("Agent", foreign_keys=[preferred_agent_id])
    department = relationship("Department")
    
    def __repr__(self) -> str:
        return f"<CallbackRequest(id={self.id}, caller='{self.caller_name}', status={self.status.value})>"
    
    @property
    def is_active(self) -> bool:
        """Check if callback request is active (not completed/cancelled/expired)."""
        active_statuses = [CallbackStatus.PENDING, CallbackStatus.SCHEDULED, CallbackStatus.IN_PROGRESS]
        return self.status in active_statuses
    
    @property
    def is_overdue(self) -> bool:
        """Check if callback is overdue."""
        if not self.scheduled_time:
            return False
        
        return datetime.utcnow() > self.scheduled_time + timedelta(hours=1)  # 1 hour grace period
    
    @property
    def is_expired(self) -> bool:
        """Check if callback request has expired."""
        if not self.time_window_end:
            # Default expiration: 7 days from creation
            expiry_time = self.created_at + timedelta(days=7)
        else:
            expiry_time = self.time_window_end
        
        return datetime.utcnow() > expiry_time
    
    @property
    def can_retry(self) -> bool:
        """Check if callback can be retried."""
        return self.attempts < self.max_attempts and not self.is_expired
    
    @property
    def priority_score(self) -> int:
        """Calculate priority score for scheduling."""
        base_score = self.priority.value * 10
        
        # Increase priority for overdue callbacks
        if self.is_overdue:
            base_score += 20
        
        # Increase priority based on number of attempts
        base_score += self.attempts * 5
        
        # Increase priority for VIP callers (if linked to VIP)
        if hasattr(self, 'vip_caller_id') and self.vip_caller_id:
            base_score += 30
        
        return base_score
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the callback request."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the callback request."""
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
    
    def calculate_next_attempt_time(self) -> datetime:
        """Calculate next callback attempt time based on retry strategy."""
        if not self.can_retry:
            return None
        
        # Exponential backoff: 15 min, 1 hour, 4 hours
        backoff_minutes = [15, 60, 240]
        
        if self.attempts < len(backoff_minutes):
            minutes = backoff_minutes[self.attempts]
        else:
            minutes = 240  # Default to 4 hours for subsequent attempts
        
        return datetime.utcnow() + timedelta(minutes=minutes)
    
    def update_attempt(self, outcome: str, notes: Optional[str] = None) -> None:
        """Update callback attempt information."""
        self.attempts += 1
        self.last_attempt_at = datetime.utcnow()
        self.outcome = outcome
        
        if notes:
            if self.system_notes:
                self.system_notes += f"\n{datetime.utcnow().isoformat()}: {notes}"
            else:
                self.system_notes = f"{datetime.utcnow().isoformat()}: {notes}"
        
        # Calculate next attempt time if needed
        if self.can_retry and outcome in ['no_answer', 'busy', 'failed']:
            self.next_attempt_at = self.calculate_next_attempt_time()
        else:
            self.next_attempt_at = None


class CallbackSchedule(BaseModel, TimestampMixin, TenantMixin):
    __tablename__ = "callback_schedule"
    """
    Callback scheduling configuration for departments and agents.
    
    Defines when callbacks can be scheduled and executed,
    including business hours, agent availability, and capacity limits.
    """
    
    # Schedule identification
    name = Column(
        String(255),
        nullable=False,
        doc="Schedule name"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Schedule description"
    )
    
    # Scope
    department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("department.id"),
        nullable=True,
        doc="Department this schedule applies to"
    )
    
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=True,
        doc="Specific agent this schedule applies to"
    )
    
    # Time configuration
    timezone = Column(
        String(50),
        nullable=False,
        default="UTC",
        doc="Timezone for this schedule"
    )
    
    business_hours_start = Column(
        String(5),
        nullable=False,
        default="09:00",
        doc="Business hours start time (HH:MM)"
    )
    
    business_hours_end = Column(
        String(5),
        nullable=False,
        default="17:00",
        doc="Business hours end time (HH:MM)"
    )
    
    business_days = Column(
        JSON,
        default=["monday", "tuesday", "wednesday", "thursday", "friday"],
        nullable=False,
        doc="Business days of the week"
    )
    
    # Capacity limits
    max_callbacks_per_hour = Column(
        Integer,
        default=10,
        nullable=False,
        doc="Maximum callbacks per hour"
    )
    
    max_callbacks_per_day = Column(
        Integer,
        default=50,
        nullable=False,
        doc="Maximum callbacks per day"
    )
    
    callback_duration_minutes = Column(
        Integer,
        default=15,
        nullable=False,
        doc="Expected callback duration in minutes"
    )
    
    # Scheduling rules
    min_advance_minutes = Column(
        Integer,
        default=30,
        nullable=False,
        doc="Minimum advance notice for scheduling"
    )
    
    max_advance_days = Column(
        Integer,
        default=7,
        nullable=False,
        doc="Maximum days in advance for scheduling"
    )
    
    allow_same_day = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether same-day callbacks are allowed"
    )
    
    # Configuration
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this schedule is active"
    )
    
    priority = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Schedule priority for conflict resolution"
    )
    
    # Relationships
    department = relationship("Department")
    agent = relationship("Agent")
    
    def __repr__(self) -> str:
        return f"<CallbackSchedule(id={self.id}, name='{self.name}')>"
    
    def is_business_time(self, check_time: datetime) -> bool:
        """Check if given time falls within business hours."""
        # Convert to schedule timezone if needed
        # For simplicity, assuming UTC for now
        
        day_name = check_time.strftime("%A").lower()
        if day_name not in self.business_days:
            return False
        
        time_str = check_time.strftime("%H:%M")
        return self.business_hours_start <= time_str <= self.business_hours_end
    
    def get_next_available_slot(self, after_time: datetime) -> Optional[datetime]:
        """Get next available callback slot after given time."""
        # Start from the next business hour
        current_time = after_time + timedelta(minutes=self.min_advance_minutes)
        
        # Find next business day/hour
        for days_ahead in range(self.max_advance_days + 1):
            check_time = current_time + timedelta(days=days_ahead)
            
            if self.is_business_time(check_time):
                # Round to next 15-minute interval
                minutes = (check_time.minute // 15 + 1) * 15
                if minutes >= 60:
                    check_time = check_time.replace(hour=check_time.hour + 1, minute=0)
                else:
                    check_time = check_time.replace(minute=minutes)
                
                # Verify still within business hours
                if self.is_business_time(check_time):
                    return check_time
        
        return None


class CallbackAttempt(BaseModel, TimestampMixin, TenantMixin):
    __tablename__ = "callback_attempt"
    """
    Individual callback attempt tracking.
    
    Records each attempt to call back a customer,
    including outcome, duration, and agent notes.
    """
    
    callback_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("callback_request.id"),
        nullable=False,
        doc="Reference to callback request"
    )
    
    attempt_number = Column(
        Integer,
        nullable=False,
        doc="Attempt sequence number"
    )
    
    # Attempt details
    attempted_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="When attempt was made"
    )
    
    attempted_by_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=True,
        doc="Agent who made the attempt"
    )
    
    # Call details
    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("call.id"),
        nullable=True,
        doc="Reference to actual call if connected"
    )
    
    outcome = Column(
        String(50),
        nullable=False,
        doc="Attempt outcome (connected, no_answer, busy, invalid_number, etc.)"
    )
    
    duration_seconds = Column(
        Integer,
        nullable=True,
        doc="Call duration if connected"
    )
    
    # Results
    caller_reached = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether caller was successfully reached"
    )
    
    issue_resolved = Column(
        Boolean,
        nullable=True,
        doc="Whether caller's issue was resolved"
    )
    
    follow_up_needed = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether follow-up is needed"
    )
    
    # Notes and feedback
    agent_notes = Column(
        Text,
        nullable=True,
        doc="Agent notes about the attempt"
    )
    
    caller_feedback = Column(
        Text,
        nullable=True,
        doc="Feedback from caller if any"
    )
    
    # Technical details
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if attempt failed"
    )
    
    retry_recommended = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether retry is recommended"
    )
    
    # Relationships
    callback_request = relationship("CallbackRequest")
    attempted_by_agent = relationship("Agent")
    call = relationship("Call")
    
    def __repr__(self) -> str:
        return f"<CallbackAttempt(id={self.id}, attempt={self.attempt_number}, outcome='{self.outcome}')>"