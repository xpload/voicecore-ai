"""
Agent-related database models for VoiceCore AI.

Defines agents, departments, and agent status management
with proper tenant isolation and hierarchy support.
"""

import enum
from typing import Optional
from sqlalchemy import Column, String, Boolean, Integer, Enum, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel, TimestampMixin, TenantMixin


class AgentStatus(enum.Enum):
    """Agent availability status enumeration."""
    AVAILABLE = "available"
    BUSY = "busy"
    NOT_AVAILABLE = "not_available"


class Agent(BaseModel, TimestampMixin, TenantMixin):
    """
    Agent model representing employees who handle calls.
    
    Agents belong to departments and have status management
    for call routing and availability tracking.
    """
    
    # Basic agent information
    email = Column(
        String(255),
        nullable=False,
        doc="Agent email address (unique per tenant)"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Agent full name"
    )
    
    first_name = Column(
        String(100),
        nullable=False,
        doc="Agent first name"
    )
    
    last_name = Column(
        String(100),
        nullable=False,
        doc="Agent last name"
    )
    
    # Extension and contact
    extension = Column(
        String(10),
        nullable=False,
        doc="Numeric extension for direct dialing"
    )
    
    phone_number = Column(
        String(20),
        nullable=True,
        doc="Agent's phone number for call forwarding"
    )
    
    # Department and hierarchy
    department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("department.id"),
        nullable=False,
        doc="Department the agent belongs to"
    )
    
    is_manager = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the agent is a department manager"
    )
    
    manager_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=True,
        doc="Reference to the agent's manager"
    )
    
    # Status and availability
    status = Column(
        Enum(AgentStatus),
        default=AgentStatus.NOT_AVAILABLE,
        nullable=False,
        doc="Current agent status"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the agent account is active"
    )
    
    last_status_change = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last status change"
    )
    
    # Work schedule and preferences
    work_schedule = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Agent work schedule configuration"
    )
    
    is_afterhours = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether agent works afterhours/weekends"
    )
    
    # Call handling preferences
    max_concurrent_calls = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Maximum concurrent calls for this agent"
    )
    
    current_calls = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current number of active calls"
    )
    
    last_call_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last call assignment"
    )
    
    routing_weight = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Routing weight for load balancing (higher = more calls)"
    )
    
    auto_answer = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether to auto-answer incoming calls"
    )
    
    # Skills and specializations
    skills = Column(
        JSON,
        default=list,
        nullable=False,
        doc="List of agent skills/specializations"
    )
    
    languages = Column(
        JSON,
        default=lambda: ["en"],
        nullable=False,
        doc="Languages the agent speaks"
    )
    
    # Performance tracking
    total_calls_handled = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of calls handled by agent"
    )
    
    average_call_duration = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Average call duration in seconds"
    )
    
    # Settings and preferences
    settings = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Agent-specific settings and preferences"
    )
    
    # Relationships
    department = relationship("Department", back_populates="agents")
    manager = relationship("Agent", remote_side=[BaseModel.id])
    voicemail_box = relationship("VoicemailBox", back_populates="agent", uselist=False)
    # calls = relationship("Call", back_populates="agent")
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', status={self.status.value})>"
    
    @property
    def full_name(self) -> str:
        """Get agent's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_available(self) -> bool:
        """Check if agent is available for calls."""
        return self.is_active and self.status == AgentStatus.AVAILABLE
    
    def get_setting(self, key: str, default=None):
        """Get a specific setting value."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value) -> None:
        """Set a specific setting value."""
        if self.settings is None:
            self.settings = {}
        self.settings[key] = value


class Department(BaseModel, TimestampMixin, TenantMixin):
    """
    Department model for organizing agents into functional groups.
    
    Departments have managers and specific functions within
    the organization for proper call routing.
    """
    
    # Basic department information
    name = Column(
        String(100),
        nullable=False,
        doc="Department name"
    )
    
    code = Column(
        String(20),
        nullable=False,
        doc="Short department code (e.g., 'CS', 'DISPATCH')"
    )
    
    description = Column(
        String(500),
        nullable=True,
        doc="Department description and function"
    )
    
    # Department configuration
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the department is active"
    )
    
    is_default = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is the default department for transfers"
    )
    
    # Call handling
    max_queue_size = Column(
        Integer,
        default=10,
        nullable=False,
        doc="Maximum number of calls in queue"
    )
    
    queue_timeout = Column(
        Integer,
        default=300,
        nullable=False,
        doc="Queue timeout in seconds"
    )
    
    # Transfer rules and keywords
    transfer_keywords = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Keywords that trigger transfer to this department"
    )
    
    # Business hours (can override tenant settings)
    business_hours = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Department-specific business hours"
    )
    
    # Voicemail configuration
    voicemail_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether voicemail is enabled for this department"
    )
    
    voicemail_greeting = Column(
        String(500),
        nullable=True,
        doc="Custom voicemail greeting message"
    )
    
    # Priority and routing
    priority = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Department priority for routing (higher = more priority)"
    )
    
    routing_strategy = Column(
        String(50),
        default="round_robin",
        nullable=False,
        doc="Call routing strategy (round_robin, least_busy, skills_based)"
    )
    
    # Settings
    settings = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Department-specific settings"
    )
    
    # Relationships
    agents = relationship("Agent", back_populates="department")
    voicemail_box = relationship("VoicemailBox", back_populates="department", uselist=False)
    
    def __repr__(self) -> str:
        return f"<Department(id={self.id}, name='{self.name}', code='{self.code}')>"
    
    @property
    def available_agents(self) -> list:
        """Get list of available agents in this department."""
        return [agent for agent in self.agents if agent.is_available]
    
    @property
    def manager(self) -> Optional['Agent']:
        """Get the department manager."""
        managers = [agent for agent in self.agents if agent.is_manager]
        return managers[0] if managers else None
    
    def get_setting(self, key: str, default=None):
        """Get a specific setting value."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value) -> None:
        """Set a specific setting value."""
        if self.settings is None:
            self.settings = {}
        self.settings[key] = value


class AgentSession(BaseModel, TimestampMixin, TenantMixin):
    """
    Agent session tracking for login/logout and status history.
    
    Tracks when agents log in/out and their status changes
    for analytics and compliance purposes.
    """
    
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent.id"),
        nullable=False,
        doc="Reference to the agent"
    )
    
    session_start = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Session start timestamp"
    )
    
    session_end = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Session end timestamp"
    )
    
    initial_status = Column(
        Enum(AgentStatus),
        nullable=False,
        doc="Agent status at session start"
    )
    
    final_status = Column(
        Enum(AgentStatus),
        nullable=True,
        doc="Agent status at session end"
    )
    
    # Session metrics
    total_calls = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total calls handled in this session"
    )
    
    total_talk_time = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total talk time in seconds"
    )
    
    # Session metadata
    user_agent = Column(
        String(500),
        nullable=True,
        doc="Browser/client user agent"
    )
    
    session_type = Column(
        String(50),
        default="web",
        nullable=False,
        doc="Session type (web, mobile, api)"
    )
    
    # Relationships
    agent = relationship("Agent")
    
    def __repr__(self) -> str:
        return f"<AgentSession(agent_id={self.agent_id}, start={self.session_start})>"
    
    @property
    def duration(self) -> Optional[int]:
        """Get session duration in seconds."""
        if self.session_end:
            return int((self.session_end - self.session_start).total_seconds())
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.session_end is None