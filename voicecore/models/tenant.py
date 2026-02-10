"""
Tenant-related database models for VoiceCore AI.

Defines the tenant entity and tenant-specific configuration
for the multitenant architecture.
"""

from typing import Optional
from sqlalchemy import Column, String, Boolean, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel, TimestampMixin


class Tenant(BaseModel, TimestampMixin):
    __tablename__ = "tenant"
    """
    Tenant model representing a company/organization using VoiceCore AI.
    
    Each tenant has isolated data and configuration, enabling
    the multitenant SaaS architecture.
    """
    
    __tablename__ = "tenants"
    
    # Basic tenant information
    name = Column(
        String(255),
        nullable=False,
        doc="Company/organization name"
    )
    
    domain = Column(
        String(255),
        unique=True,
        nullable=True,
        doc="Custom domain for tenant (optional)"
    )
    
    subdomain = Column(
        String(100),
        unique=True,
        nullable=True,
        doc="Subdomain for tenant access"
    )
    
    # Status and configuration
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the tenant is active"
    )
    
    plan_type = Column(
        String(50),
        default="basic",
        nullable=False,
        doc="Subscription plan type (basic, professional, enterprise)"
    )
    
    # Contact information
    contact_email = Column(
        String(255),
        nullable=False,
        doc="Primary contact email for the tenant"
    )
    
    contact_phone = Column(
        String(20),
        nullable=True,
        doc="Primary contact phone number"
    )
    
    # Billing and limits
    monthly_credit_limit = Column(
        Integer,
        default=1000,
        nullable=False,
        doc="Monthly call minutes limit"
    )
    
    current_usage = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current month usage in minutes"
    )
    
    # Configuration
    settings = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Tenant-specific configuration settings"
    )
    
    # Twilio configuration
    twilio_phone_number = Column(
        String(20),
        nullable=True,
        doc="Dedicated Twilio phone number for this tenant"
    )
    
    # Relationships
    # agents = relationship("Agent", back_populates="tenant", cascade="all, delete-orphan")
    # calls = relationship("Call", back_populates="tenant", cascade="all, delete-orphan")
    voicemail_boxes = relationship("VoicemailBox", back_populates="tenant", cascade="all, delete-orphan")
    subscription = relationship("TenantSubscription", back_populates="tenant", uselist=False)
    ai_personalities = relationship("AIPersonality", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}', active={self.is_active})>"
    
    @property
    def is_over_limit(self) -> bool:
        """Check if tenant has exceeded their monthly credit limit."""
        return self.current_usage >= self.monthly_credit_limit
    
    @property
    def remaining_credits(self) -> int:
        """Get remaining credits for the month."""
        return max(0, self.monthly_credit_limit - self.current_usage)
    
    def get_setting(self, key: str, default=None):
        """Get a specific setting value."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value) -> None:
        """Set a specific setting value."""
        if self.settings is None:
            self.settings = {}
        self.settings[key] = value


class TenantSettings(BaseModel, TimestampMixin):
    """
    Extended tenant configuration settings.
    
    Stores detailed configuration for AI behavior, call handling,
    and business rules specific to each tenant.
    """
    
    __tablename__ = "tenant_settings"
    
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        doc="Reference to the tenant"
    )
    
    # AI Configuration
    ai_name = Column(
        String(100),
        default="Sofia",
        nullable=False,
        doc="Name of the AI receptionist"
    )
    
    ai_gender = Column(
        String(10),
        default="female",
        nullable=False,
        doc="AI voice gender (male/female)"
    )
    
    ai_voice_id = Column(
        String(50),
        default="alloy",
        nullable=False,
        doc="OpenAI voice ID for speech synthesis"
    )
    
    ai_personality = Column(
        Text,
        nullable=True,
        doc="AI personality and behavior instructions"
    )
    
    # Company Information
    company_description = Column(
        Text,
        nullable=True,
        doc="Description of the company for AI context"
    )
    
    company_services = Column(
        JSON,
        default=list,
        nullable=False,
        doc="List of services the company provides"
    )
    
    # Call Handling Configuration
    max_transfer_attempts = Column(
        Integer,
        default=3,
        nullable=False,
        doc="Maximum AI attempts before transferring to human"
    )
    
    default_department = Column(
        String(100),
        default="customer_service",
        nullable=False,
        doc="Default department for transfers"
    )
    
    # Business Hours
    business_hours_start = Column(
        String(5),
        default="09:00",
        nullable=False,
        doc="Business hours start time (HH:MM)"
    )
    
    business_hours_end = Column(
        String(5),
        default="17:00",
        nullable=False,
        doc="Business hours end time (HH:MM)"
    )
    
    timezone = Column(
        String(50),
        default="UTC",
        nullable=False,
        doc="Company timezone"
    )
    
    business_days = Column(
        JSON,
        default=lambda: ["monday", "tuesday", "wednesday", "thursday", "friday"],
        nullable=False,
        doc="List of business days"
    )
    
    # Feature Flags
    enable_spam_detection = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable spam call detection"
    )
    
    enable_call_recording = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable call recording"
    )
    
    enable_transcription = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable call transcription"
    )
    
    enable_emotion_detection = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Enable emotion detection in calls"
    )
    
    enable_vip_handling = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable VIP caller handling"
    )
    
    # Language Settings
    primary_language = Column(
        String(10),
        default="auto",
        nullable=False,
        doc="Primary language (auto, en, es)"
    )
    
    supported_languages = Column(
        JSON,
        default=lambda: ["en", "es"],
        nullable=False,
        doc="List of supported languages"
    )
    
    # Custom Messages
    welcome_message = Column(
        Text,
        nullable=True,
        doc="Custom welcome message for callers"
    )
    
    afterhours_message = Column(
        Text,
        nullable=True,
        doc="Message for calls outside business hours"
    )
    
    voicemail_message = Column(
        Text,
        nullable=True,
        doc="Custom voicemail greeting message"
    )
    
    # Transfer Rules (JSON configuration)
    transfer_rules = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Custom transfer rules configuration"
    )
    
    # Spam Detection Rules
    spam_keywords = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Keywords for spam detection"
    )
    
    # VIP Configuration
    vip_phone_numbers = Column(
        JSON,
        default=list,
        nullable=False,
        doc="List of VIP phone numbers"
    )
    
    def __repr__(self) -> str:
        return f"<TenantSettings(tenant_id={self.tenant_id}, ai_name='{self.ai_name}')>"