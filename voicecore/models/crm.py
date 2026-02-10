"""
CRM (Customer Relationship Management) models for VoiceCore AI 2.0.

Defines contacts, leads, interactions, pipeline stages, and sales tracking
for integrated CRM functionality.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, 
    ForeignKey, JSON, Index, Float, Date
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from voicecore.models.base import BaseModel


class CRMContact(BaseModel):
    """
    CRM contact model for managing customer information.
    
    Stores customer/prospect information with custom fields,
    tags, and interaction history.
    """
    __tablename__ = "crm_contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Basic information
    first_name = Column(String(100), nullable=False, doc="Contact first name")
    last_name = Column(String(100), nullable=False, doc="Contact last name")
    email = Column(String(255), nullable=True, doc="Contact email address")
    phone = Column(String(20), nullable=True, doc="Contact phone number")
    mobile = Column(String(20), nullable=True, doc="Contact mobile number")
    
    # Company information
    company = Column(String(255), nullable=True, doc="Company name")
    job_title = Column(String(100), nullable=True, doc="Job title")
    department = Column(String(100), nullable=True, doc="Department")
    
    # Address information
    address_line1 = Column(String(255), nullable=True, doc="Address line 1")
    address_line2 = Column(String(255), nullable=True, doc="Address line 2")
    city = Column(String(100), nullable=True, doc="City")
    state = Column(String(100), nullable=True, doc="State/Province")
    postal_code = Column(String(20), nullable=True, doc="Postal/ZIP code")
    country = Column(String(100), nullable=True, doc="Country")
    
    # Lead scoring and status
    lead_score = Column(Integer, default=0, nullable=False, doc="Lead score (0-100)")
    status = Column(String(50), default="new", nullable=False, doc="Contact status")
    lifecycle_stage = Column(String(50), default="lead", nullable=False, doc="Lifecycle stage")
    
    # Source and attribution
    source = Column(String(100), nullable=True, doc="Lead source")
    campaign = Column(String(100), nullable=True, doc="Marketing campaign")
    referrer = Column(String(255), nullable=True, doc="Referrer URL or source")
    
    # Engagement metrics
    total_interactions = Column(Integer, default=0, nullable=False, doc="Total number of interactions")
    last_interaction_date = Column(DateTime, nullable=True, doc="Last interaction timestamp")
    first_interaction_date = Column(DateTime, nullable=True, doc="First interaction timestamp")
    
    # Preferences
    preferred_contact_method = Column(String(50), nullable=True, doc="Preferred contact method")
    preferred_language = Column(String(10), nullable=True, doc="Preferred language code")
    timezone = Column(String(50), nullable=True, doc="Contact timezone")
    
    # Custom fields and tags
    tags = Column(JSON, default=list, nullable=False, doc="Contact tags")
    custom_fields = Column(JSON, default=dict, nullable=False, doc="Custom field values")
    
    # Social media
    linkedin_url = Column(String(255), nullable=True, doc="LinkedIn profile URL")
    twitter_handle = Column(String(100), nullable=True, doc="Twitter handle")
    
    # Notes and description
    description = Column(Text, nullable=True, doc="Contact description/notes")
    
    # Assignment
    owner_id = Column(UUID(as_uuid=True), nullable=True, doc="Assigned user/agent ID")
    
    # Status flags
    is_active = Column(Boolean, default=True, nullable=False, doc="Whether contact is active")
    is_vip = Column(Boolean, default=False, nullable=False, doc="Whether contact is VIP")
    do_not_call = Column(Boolean, default=False, nullable=False, doc="Do not call flag")
    do_not_email = Column(Boolean, default=False, nullable=False, doc="Do not email flag")
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    interactions = relationship("CRMInteraction", back_populates="contact", cascade="all, delete-orphan")
    leads = relationship("CRMLead", back_populates="contact", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_crm_contact_tenant", "tenant_id"),
        Index("idx_crm_contact_email", "email"),
        Index("idx_crm_contact_phone", "phone"),
        Index("idx_crm_contact_status", "status"),
        Index("idx_crm_contact_score", "lead_score"),
        Index("idx_crm_contact_name", "first_name", "last_name"),
    )
    
    @property
    def full_name(self) -> str:
        """Get full name of contact."""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<CRMContact(id={self.id}, name='{self.full_name}', email='{self.email}')>"


class CRMLead(BaseModel):
    """
    CRM lead model for sales pipeline management.
    
    Tracks leads through the sales pipeline with stages,
    values, and conversion tracking.
    """
    __tablename__ = "crm_leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("crm_contacts.id"), nullable=False)
    
    # Lead information
    title = Column(String(255), nullable=False, doc="Lead/opportunity title")
    description = Column(Text, nullable=True, doc="Lead description")
    
    # Pipeline and stage
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("crm_pipelines.id"), nullable=False)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id"), nullable=False)
    
    # Value and probability
    estimated_value = Column(Integer, default=0, nullable=False, doc="Estimated value in cents")
    probability = Column(Integer, default=0, nullable=False, doc="Win probability (0-100)")
    expected_close_date = Column(Date, nullable=True, doc="Expected close date")
    
    # Status
    status = Column(String(50), default="open", nullable=False, doc="Lead status")
    is_qualified = Column(Boolean, default=False, nullable=False, doc="Whether lead is qualified")
    
    # Assignment
    owner_id = Column(UUID(as_uuid=True), nullable=True, doc="Assigned sales rep ID")
    
    # Source and attribution
    source = Column(String(100), nullable=True, doc="Lead source")
    campaign = Column(String(100), nullable=True, doc="Marketing campaign")
    
    # Outcome tracking
    won_date = Column(DateTime, nullable=True, doc="Date lead was won")
    lost_date = Column(DateTime, nullable=True, doc="Date lead was lost")
    lost_reason = Column(String(255), nullable=True, doc="Reason for loss")
    actual_value = Column(Integer, nullable=True, doc="Actual closed value in cents")
    
    # Engagement
    last_activity_date = Column(DateTime, nullable=True, doc="Last activity timestamp")
    next_follow_up_date = Column(DateTime, nullable=True, doc="Next follow-up date")
    
    # Custom fields
    custom_fields = Column(JSON, default=dict, nullable=False, doc="Custom field values")
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    contact = relationship("CRMContact", back_populates="leads")
    pipeline = relationship("CRMPipeline", back_populates="leads")
    stage = relationship("CRMPipelineStage", back_populates="leads")
    activities = relationship("CRMActivity", back_populates="lead", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_crm_lead_tenant", "tenant_id"),
        Index("idx_crm_lead_contact", "contact_id"),
        Index("idx_crm_lead_pipeline", "pipeline_id"),
        Index("idx_crm_lead_stage", "stage_id"),
        Index("idx_crm_lead_status", "status"),
        Index("idx_crm_lead_owner", "owner_id"),
    )
    
    @property
    def weighted_value(self) -> int:
        """Calculate weighted value based on probability."""
        return int(self.estimated_value * (self.probability / 100))
    
    def __repr__(self):
        return f"<CRMLead(id={self.id}, title='{self.title}', status='{self.status}')>"


class CRMPipeline(BaseModel):
    """
    CRM pipeline model for sales process definition.
    
    Defines sales pipelines with stages and conversion tracking.
    """
    __tablename__ = "crm_pipelines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Pipeline configuration
    name = Column(String(255), nullable=False, doc="Pipeline name")
    description = Column(Text, nullable=True, doc="Pipeline description")
    is_active = Column(Boolean, default=True, nullable=False, doc="Whether pipeline is active")
    is_default = Column(Boolean, default=False, nullable=False, doc="Whether this is the default pipeline")
    
    # Metrics
    total_leads = Column(Integer, default=0, nullable=False, doc="Total leads in pipeline")
    total_value = Column(Integer, default=0, nullable=False, doc="Total pipeline value in cents")
    conversion_rate = Column(Float, default=0.0, nullable=False, doc="Overall conversion rate")
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    stages = relationship("CRMPipelineStage", back_populates="pipeline", cascade="all, delete-orphan", order_by="CRMPipelineStage.order")
    leads = relationship("CRMLead", back_populates="pipeline")
    
    # Indexes
    __table_args__ = (
        Index("idx_crm_pipeline_tenant", "tenant_id"),
        Index("idx_crm_pipeline_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<CRMPipeline(id={self.id}, name='{self.name}')>"


class CRMPipelineStage(BaseModel):
    """
    CRM pipeline stage model for sales process steps.
    
    Defines stages within a pipeline with conversion tracking.
    """
    __tablename__ = "crm_pipeline_stages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("crm_pipelines.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Stage configuration
    name = Column(String(255), nullable=False, doc="Stage name")
    description = Column(Text, nullable=True, doc="Stage description")
    order = Column(Integer, nullable=False, doc="Stage order in pipeline")
    
    # Stage type
    stage_type = Column(String(50), default="active", nullable=False, doc="Stage type (active, won, lost)")
    probability = Column(Integer, default=0, nullable=False, doc="Default probability for this stage")
    
    # Metrics
    leads_count = Column(Integer, default=0, nullable=False, doc="Number of leads in this stage")
    total_value = Column(Integer, default=0, nullable=False, doc="Total value of leads in cents")
    average_time_in_stage = Column(Integer, default=0, nullable=False, doc="Average time in stage (days)")
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pipeline = relationship("CRMPipeline", back_populates="stages")
    leads = relationship("CRMLead", back_populates="stage")
    
    # Indexes
    __table_args__ = (
        Index("idx_crm_stage_pipeline", "pipeline_id"),
        Index("idx_crm_stage_order", "pipeline_id", "order"),
    )
    
    def __repr__(self):
        return f"<CRMPipelineStage(id={self.id}, name='{self.name}', order={self.order})>"


class CRMInteraction(BaseModel):
    """
    CRM interaction model for tracking customer touchpoints.
    
    Records all interactions with contacts including calls,
    emails, meetings, and notes.
    """
    __tablename__ = "crm_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("crm_contacts.id"), nullable=False)
    
    # Interaction details
    interaction_type = Column(String(50), nullable=False, doc="Type of interaction")
    subject = Column(String(255), nullable=True, doc="Interaction subject")
    description = Column(Text, nullable=True, doc="Interaction description/notes")
    
    # Related entities
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("crm_leads.id"), nullable=True)
    
    # Timing
    interaction_date = Column(DateTime, nullable=False, default=datetime.utcnow, doc="When interaction occurred")
    duration_seconds = Column(Integer, nullable=True, doc="Duration in seconds")
    
    # Outcome
    outcome = Column(String(100), nullable=True, doc="Interaction outcome")
    sentiment = Column(String(50), nullable=True, doc="Sentiment analysis result")
    
    # Assignment
    created_by = Column(UUID(as_uuid=True), nullable=True, doc="User who created this interaction")
    
    # Metadata
    crm_metadata = Column("metadata", JSON, default=dict, nullable=False, doc="Additional metadata")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    contact = relationship("CRMContact", back_populates="interactions")
    
    # Indexes
    __table_args__ = (
        Index("idx_crm_interaction_tenant", "tenant_id"),
        Index("idx_crm_interaction_contact", "contact_id"),
        Index("idx_crm_interaction_type", "interaction_type"),
        Index("idx_crm_interaction_date", "interaction_date"),
    )
    
    def __repr__(self):
        return f"<CRMInteraction(id={self.id}, type='{self.interaction_type}', contact_id={self.contact_id})>"


class CRMActivity(BaseModel):
    """
    CRM activity model for tracking sales activities.
    
    Records planned and completed activities for leads
    including tasks, calls, meetings, and follow-ups.
    """
    __tablename__ = "crm_activities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("crm_leads.id"), nullable=False)
    
    # Activity details
    activity_type = Column(String(50), nullable=False, doc="Type of activity")
    subject = Column(String(255), nullable=False, doc="Activity subject")
    description = Column(Text, nullable=True, doc="Activity description")
    
    # Scheduling
    scheduled_date = Column(DateTime, nullable=True, doc="Scheduled date/time")
    completed_date = Column(DateTime, nullable=True, doc="Completion date/time")
    due_date = Column(DateTime, nullable=True, doc="Due date")
    
    # Status
    status = Column(String(50), default="planned", nullable=False, doc="Activity status")
    priority = Column(String(20), default="normal", nullable=False, doc="Activity priority")
    
    # Assignment
    assigned_to = Column(UUID(as_uuid=True), nullable=True, doc="Assigned user ID")
    
    # Outcome
    outcome = Column(String(100), nullable=True, doc="Activity outcome")
    notes = Column(Text, nullable=True, doc="Activity notes")
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lead = relationship("CRMLead", back_populates="activities")
    
    # Indexes
    __table_args__ = (
        Index("idx_crm_activity_tenant", "tenant_id"),
        Index("idx_crm_activity_lead", "lead_id"),
        Index("idx_crm_activity_type", "activity_type"),
        Index("idx_crm_activity_status", "status"),
        Index("idx_crm_activity_assigned", "assigned_to"),
        Index("idx_crm_activity_due", "due_date"),
    )
    
    def __repr__(self):
        return f"<CRMActivity(id={self.id}, type='{self.activity_type}', status='{self.status}')>"
