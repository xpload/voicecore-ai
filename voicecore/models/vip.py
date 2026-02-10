"""
VIP caller management models for VoiceCore AI.

Defines VIP caller entities, priority levels, and special handling rules
for premium customer experience in the multitenant system.
"""

import enum
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Enum, ForeignKey, JSON, DateTime, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel, TimestampMixin, TenantMixin


class VIPPriority(enum.Enum):
    """VIP priority levels for call routing."""
    STANDARD = 1
    SILVER = 2
    GOLD = 3
    PLATINUM = 4
    DIAMOND = 5


class VIPStatus(enum.Enum):
    """VIP caller status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class VIPHandlingRule(enum.Enum):
    """VIP handling rule types."""
    IMMEDIATE_TRANSFER = "immediate_transfer"
    PRIORITY_QUEUE = "priority_queue"
    DEDICATED_AGENT = "dedicated_agent"
    CALLBACK_PRIORITY = "callback_priority"
    EXTENDED_HOURS = "extended_hours"
    CUSTOM_GREETING = "custom_greeting"


class VIPCaller(BaseModel, TimestampMixin, TenantMixin):
    __tablename__ = "v_i_p_caller"
    """
    VIP caller model for managing premium customers.
    
    Tracks VIP customers with special handling rules, priority levels,
    and custom configurations for enhanced customer experience.
    """
    
    # Caller identification
    phone_number = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Hashed phone number for privacy compliance"
    )
    
    caller_name = Column(
        String(255),
        nullable=False,
        doc="VIP caller's name"
    )
    
    company_name = Column(
        String(255),
        nullable=True,
        doc="VIP caller's company name"
    )
    
    # VIP configuration
    vip_level = Column(
        Enum(VIPPriority),
        default=VIPPriority.STANDARD,
        nullable=False,
        doc="VIP priority level"
    )
    
    status = Column(
        Enum(VIPStatus),
        default=VIPStatus.ACTIVE,
        nullable=False,
        doc="VIP status"
    )
    
    # Handling preferences
    preferred_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=True,
        doc="Preferred agent for this VIP caller"
    )
    
    preferred_department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("department.id"),
        nullable=True,
        doc="Preferred department for routing"
    )
    
    handling_rules = Column(
        JSON,
        default=list,
        nullable=False,
        doc="List of special handling rules"
    )
    
    # Custom configurations
    custom_greeting = Column(
        Text,
        nullable=True,
        doc="Custom greeting message for this VIP"
    )
    
    custom_hold_music = Column(
        String(500),
        nullable=True,
        doc="URL to custom hold music"
    )
    
    max_wait_time = Column(
        Integer,
        default=60,
        nullable=False,
        doc="Maximum wait time in seconds before escalation"
    )
    
    callback_priority = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Callback priority (1=highest)"
    )
    
    # Contact information
    email = Column(
        String(255),
        nullable=True,
        doc="VIP caller's email address"
    )
    
    alternative_phone = Column(
        String(255),
        nullable=True,
        doc="Alternative phone number (hashed)"
    )
    
    # Account information
    account_number = Column(
        String(100),
        nullable=True,
        doc="Customer account number"
    )
    
    account_value = Column(
        Float,
        nullable=True,
        doc="Account value for priority calculation"
    )
    
    # Validity and expiration
    valid_from = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="VIP status valid from date"
    )
    
    valid_until = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="VIP status expiration date"
    )
    
    # Usage tracking
    total_calls = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of calls from this VIP"
    )
    
    last_call_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last call"
    )
    
    average_call_duration = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Average call duration in seconds"
    )
    
    satisfaction_score = Column(
        Float,
        nullable=True,
        doc="Average satisfaction score (1-5)"
    )
    
    # Notes and tags
    notes = Column(
        Text,
        nullable=True,
        doc="Internal notes about this VIP caller"
    )
    
    tags = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Tags for categorization"
    )
    
    # Metadata
    vip_metadata = Column("metadata", 
        JSON,
        default=dict,
        nullable=False,
        doc="Additional VIP-specific metadata"
    )
    
    # Relationships
    preferred_agent = relationship("Agent", foreign_keys=[preferred_agent_id])
    preferred_department = relationship("Department", foreign_keys=[preferred_department_id])
    
    def __repr__(self) -> str:
        return f"<VIPCaller(id={self.id}, name='{self.caller_name}', level={self.vip_level.value})>"
    
    @property
    def is_active(self) -> bool:
        """Check if VIP status is currently active."""
        if self.status != VIPStatus.ACTIVE:
            return False
        
        now = datetime.utcnow()
        
        if self.valid_until and now > self.valid_until:
            return False
        
        return now >= self.valid_from
    
    @property
    def priority_score(self) -> int:
        """Calculate priority score for routing decisions."""
        base_score = self.vip_level.value * 10
        
        # Bonus for account value
        if self.account_value:
            if self.account_value > 100000:
                base_score += 20
            elif self.account_value > 50000:
                base_score += 10
            elif self.account_value > 10000:
                base_score += 5
        
        # Bonus for satisfaction score
        if self.satisfaction_score and self.satisfaction_score >= 4.5:
            base_score += 5
        
        return base_score
    
    def has_handling_rule(self, rule: VIPHandlingRule) -> bool:
        """Check if VIP has a specific handling rule."""
        return rule.value in (self.handling_rules or [])
    
    def add_handling_rule(self, rule: VIPHandlingRule) -> None:
        """Add a handling rule to the VIP."""
        if self.handling_rules is None:
            self.handling_rules = []
        
        if rule.value not in self.handling_rules:
            self.handling_rules.append(rule.value)
    
    def remove_handling_rule(self, rule: VIPHandlingRule) -> None:
        """Remove a handling rule from the VIP."""
        if self.handling_rules and rule.value in self.handling_rules:
            self.handling_rules.remove(rule.value)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the VIP."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the VIP."""
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
    
    def update_call_stats(self, call_duration: int, satisfaction: Optional[float] = None) -> None:
        """Update call statistics for this VIP."""
        self.total_calls += 1
        self.last_call_at = datetime.utcnow()
        
        # Update average call duration
        if self.average_call_duration == 0:
            self.average_call_duration = call_duration
        else:
            self.average_call_duration = int(
                (self.average_call_duration * (self.total_calls - 1) + call_duration) / self.total_calls
            )
        
        # Update satisfaction score
        if satisfaction is not None:
            if self.satisfaction_score is None:
                self.satisfaction_score = satisfaction
            else:
                # Weighted average with more weight on recent calls
                weight = 0.3  # 30% weight for new score
                self.satisfaction_score = (1 - weight) * self.satisfaction_score + weight * satisfaction


class VIPCallHistory(BaseModel, TimestampMixin, TenantMixin):
    __tablename__ = "v_i_p_call_history"
    """
    VIP call history tracking for analytics and service improvement.
    
    Records detailed information about VIP calls for analysis
    and continuous improvement of VIP service quality.
    """
    
    vip_caller_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vip_caller.id"),
        nullable=False,
        doc="Reference to VIP caller"
    )
    
    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("call.id"),
        nullable=False,
        doc="Reference to the call"
    )
    
    # VIP-specific call details
    vip_level_at_call = Column(
        Enum(VIPPriority),
        nullable=False,
        doc="VIP level at the time of call"
    )
    
    handling_rules_applied = Column(
        JSON,
        default=list,
        nullable=False,
        doc="VIP handling rules that were applied"
    )
    
    preferred_agent_available = Column(
        Boolean,
        nullable=True,
        doc="Whether preferred agent was available"
    )
    
    routed_to_preferred = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether call was routed to preferred agent/department"
    )
    
    # Service quality metrics
    wait_time_seconds = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Actual wait time in seconds"
    )
    
    escalation_triggered = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether escalation was triggered due to wait time"
    )
    
    custom_greeting_used = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether custom greeting was used"
    )
    
    satisfaction_rating = Column(
        Integer,
        nullable=True,
        doc="Post-call satisfaction rating (1-5)"
    )
    
    service_quality_score = Column(
        Float,
        nullable=True,
        doc="Calculated service quality score"
    )
    
    # Resolution tracking
    issue_resolved = Column(
        Boolean,
        nullable=True,
        doc="Whether the issue was resolved"
    )
    
    resolution_time = Column(
        Integer,
        nullable=True,
        doc="Time to resolution in seconds"
    )
    
    follow_up_scheduled = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether follow-up was scheduled"
    )
    
    # Feedback and notes
    caller_feedback = Column(
        Text,
        nullable=True,
        doc="Feedback provided by the VIP caller"
    )
    
    agent_notes = Column(
        Text,
        nullable=True,
        doc="Notes added by the handling agent"
    )
    
    # Relationships
    vip_caller = relationship("VIPCaller")
    call = relationship("Call")
    
    def __repr__(self) -> str:
        return f"<VIPCallHistory(vip_id={self.vip_caller_id}, call_id={self.call_id})>"


class VIPEscalationRule(BaseModel, TimestampMixin, TenantMixin):
    __tablename__ = "v_i_p_escalation_rule"
    """
    VIP escalation rules for automatic escalation based on conditions.
    
    Defines conditions and actions for automatic escalation of VIP calls
    to ensure premium service levels are maintained.
    """
    
    name = Column(
        String(255),
        nullable=False,
        doc="Rule name"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Rule description"
    )
    
    # Trigger conditions
    vip_levels = Column(
        JSON,
        default=list,
        nullable=False,
        doc="VIP levels this rule applies to"
    )
    
    max_wait_time = Column(
        Integer,
        nullable=True,
        doc="Maximum wait time before escalation (seconds)"
    )
    
    max_queue_position = Column(
        Integer,
        nullable=True,
        doc="Maximum queue position before escalation"
    )
    
    time_of_day_start = Column(
        String(5),
        nullable=True,
        doc="Start time for rule activation (HH:MM)"
    )
    
    time_of_day_end = Column(
        String(5),
        nullable=True,
        doc="End time for rule activation (HH:MM)"
    )
    
    days_of_week = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Days of week this rule is active"
    )
    
    # Escalation actions
    escalation_type = Column(
        String(50),
        nullable=False,
        doc="Type of escalation (manager, department, agent)"
    )
    
    escalation_target_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Target agent/department ID for escalation"
    )
    
    notification_emails = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Email addresses to notify on escalation"
    )
    
    notification_message = Column(
        Text,
        nullable=True,
        doc="Custom notification message"
    )
    
    # Rule configuration
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the rule is active"
    )
    
    priority = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Rule priority (higher = more priority)"
    )
    
    # Usage tracking
    times_triggered = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of times this rule was triggered"
    )
    
    last_triggered_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last time this rule was triggered"
    )
    
    def __repr__(self) -> str:
        return f"<VIPEscalationRule(id={self.id}, name='{self.name}')>"
    
    def is_applicable(self, vip_level: VIPPriority, current_time: datetime) -> bool:
        """Check if rule is applicable for given VIP level and time."""
        if not self.is_active:
            return False
        
        # Check VIP level
        if self.vip_levels and vip_level.value not in self.vip_levels:
            return False
        
        # Check time of day
        if self.time_of_day_start and self.time_of_day_end:
            current_time_str = current_time.strftime("%H:%M")
            if not (self.time_of_day_start <= current_time_str <= self.time_of_day_end):
                return False
        
        # Check day of week
        if self.days_of_week:
            current_day = current_time.strftime("%A").lower()
            if current_day not in [day.lower() for day in self.days_of_week]:
                return False
        
        return True
    
    def should_escalate(self, wait_time: int, queue_position: int) -> bool:
        """Check if escalation should be triggered based on conditions."""
        if self.max_wait_time and wait_time >= self.max_wait_time:
            return True
        
        if self.max_queue_position and queue_position >= self.max_queue_position:
            return True
        
        return False