"""
Security models for VoiceCore AI.

Defines models for security configurations, audit logs,
and privacy compliance tracking.
"""

import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, JSON, Text, Enum
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel, TimestampMixin, TenantMixin


class SecurityEventType(enum.Enum):
    """Security event types for monitoring."""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_DENIED = "permission_denied"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    CONFIGURATION_CHANGE = "configuration_change"
    THREAT_DETECTED = "threat_detected"
    INTRUSION_ATTEMPT = "intrusion_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class SecurityConfiguration(BaseModel, TimestampMixin, TenantMixin):
    __tablename__ = "security_configuration"
    """
    Security configuration settings per tenant.
    
    Stores tenant-specific security policies and settings
    for privacy compliance and threat protection.
    """
    
    # Rate limiting configuration
    api_rate_limit = Column(
        Integer,
        default=200,
        nullable=False,
        doc="API requests per minute limit"
    )
    
    auth_rate_limit = Column(
        Integer,
        default=10,
        nullable=False,
        doc="Authentication attempts per minute limit"
    )
    
    # Security policies
    require_strong_passwords = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Require strong password policy"
    )
    
    enable_two_factor_auth = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Enable two-factor authentication"
    )
    
    session_timeout_minutes = Column(
        Integer,
        default=60,
        nullable=False,
        doc="Session timeout in minutes"
    )
    
    max_failed_attempts = Column(
        Integer,
        default=5,
        nullable=False,
        doc="Maximum failed login attempts before lockout"
    )
    
    lockout_duration_minutes = Column(
        Integer,
        default=15,
        nullable=False,
        doc="Account lockout duration in minutes"
    )
    
    # Data encryption settings
    encrypt_call_recordings = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Encrypt call recordings at rest"
    )
    
    encrypt_transcripts = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Encrypt call transcripts"
    )
    
    encrypt_customer_data = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Encrypt customer data fields"
    )
    
    # Privacy compliance settings
    data_retention_days = Column(
        Integer,
        default=365,
        nullable=False,
        doc="Data retention period in days"
    )
    
    auto_delete_recordings = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Automatically delete old recordings"
    )
    
    anonymize_analytics = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Anonymize data in analytics"
    )
    
    # Audit and monitoring
    enable_audit_logging = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable comprehensive audit logging"
    )
    
    log_data_access = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Log all data access events"
    )
    
    alert_on_suspicious_activity = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Send alerts for suspicious activity"
    )
    
    # Intrusion detection settings
    enable_intrusion_detection = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable intrusion detection system"
    )
    
    block_suspicious_requests = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Automatically block suspicious requests"
    )
    
    threat_sensitivity = Column(
        String(20),
        default="medium",
        nullable=False,
        doc="Threat detection sensitivity (low, medium, high)"
    )
    
    # Additional security settings
    allowed_ip_ranges = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Allowed IP ranges (empty = allow all)"
    )
    
    blocked_countries = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Blocked country codes"
    )
    
    security_headers = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Custom security headers"
    )
    
    # Compliance settings
    gdpr_compliance = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable GDPR compliance features"
    )
    
    ccpa_compliance = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Enable CCPA compliance features"
    )
    
    hipaa_compliance = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Enable HIPAA compliance features"
    )
    
    def __repr__(self) -> str:
        return f"<SecurityConfiguration(tenant_id={self.tenant_id})>"


class SecurityEvent(BaseModel, TimestampMixin, TenantMixin):
    __tablename__ = "security_event"
    """
    Security event log for monitoring and compliance.
    
    Records security-related events for audit trails and
    threat analysis while maintaining privacy compliance.
    """
    
    # Event identification
    event_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        doc="Unique event identifier"
    )
    
    event_type = Column(
        Enum(SecurityEventType),
        nullable=False,
        doc="Type of security event"
    )
    
    # Event details
    severity = Column(
        String(20),
        default="info",
        nullable=False,
        doc="Event severity (info, warning, error, critical)"
    )
    
    source = Column(
        String(100),
        nullable=False,
        doc="Source of the event (service, component, etc.)"
    )
    
    action = Column(
        String(255),
        nullable=False,
        doc="Action that triggered the event"
    )
    
    resource = Column(
        String(255),
        nullable=True,
        doc="Resource involved in the event"
    )
    
    # User and session (privacy-compliant)
    user_id_hash = Column(
        String(255),
        nullable=True,
        doc="Hashed user identifier for privacy"
    )
    
    session_id_hash = Column(
        String(255),
        nullable=True,
        doc="Hashed session identifier"
    )
    
    correlation_id = Column(
        String(255),
        nullable=True,
        doc="Request correlation ID"
    )
    
    # Event outcome
    success = Column(
        Boolean,
        nullable=False,
        doc="Whether the action was successful"
    )
    
    error_code = Column(
        String(50),
        nullable=True,
        doc="Error code if action failed"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message (sanitized)"
    )
    
    # Context data (sanitized)
    event_data = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional event data (privacy-compliant)"
    )
    
    # Security analysis
    threat_level = Column(
        String(20),
        nullable=True,
        doc="Assessed threat level (low, medium, high, critical)"
    )
    
    blocked = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the action was blocked"
    )
    
    # Response and mitigation
    response_action = Column(
        String(100),
        nullable=True,
        doc="Automated response action taken"
    )
    
    mitigation_applied = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether mitigation was applied"
    )
    
    # Additional metadata
    user_agent_hash = Column(
        String(255),
        nullable=True,
        doc="Hashed user agent for analysis"
    )
    
    request_method = Column(
        String(10),
        nullable=True,
        doc="HTTP request method"
    )
    
    request_path = Column(
        String(500),
        nullable=True,
        doc="Request path (sanitized)"
    )
    
    response_status = Column(
        Integer,
        nullable=True,
        doc="HTTP response status code"
    )
    
    processing_time_ms = Column(
        Float,
        nullable=True,
        doc="Request processing time in milliseconds"
    )
    
    def __repr__(self) -> str:
        return f"<SecurityEvent(event_id={self.event_id}, type={self.event_type.value})>"


class ThreatIntelligence(BaseModel, TimestampMixin):
    __tablename__ = "threat_intelligence"
    """
    Threat intelligence data for enhanced security.
    
    Stores known threat patterns, malicious signatures,
    and security intelligence for proactive protection.
    """
    
    # Threat identification
    threat_id = Column(
        String(100),
        nullable=False,
        unique=True,
        doc="Unique threat identifier"
    )
    
    threat_type = Column(
        String(50),
        nullable=False,
        doc="Type of threat (malware, phishing, etc.)"
    )
    
    threat_name = Column(
        String(255),
        nullable=False,
        doc="Human-readable threat name"
    )
    
    # Threat details
    description = Column(
        Text,
        nullable=True,
        doc="Detailed threat description"
    )
    
    severity_score = Column(
        Float,
        nullable=False,
        doc="Threat severity score (0.0 to 10.0)"
    )
    
    confidence_level = Column(
        Float,
        nullable=False,
        doc="Confidence in threat assessment (0.0 to 1.0)"
    )
    
    # Detection patterns
    signatures = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Detection signatures and patterns"
    )
    
    indicators = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Indicators of compromise (IoCs)"
    )
    
    # Threat metadata
    first_seen = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="When threat was first observed"
    )
    
    last_seen = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="When threat was last observed"
    )
    
    source = Column(
        String(100),
        nullable=False,
        doc="Threat intelligence source"
    )
    
    # Status and lifecycle
    active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether threat is currently active"
    )
    
    false_positive_rate = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Known false positive rate"
    )
    
    # Response actions
    recommended_action = Column(
        String(50),
        nullable=False,
        doc="Recommended response action"
    )
    
    auto_block = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether to automatically block this threat"
    )
    
    # Additional metadata
    tags = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Threat classification tags"
    )
    
    references = Column(
        JSON,
        default=list,
        nullable=False,
        doc="External references and sources"
    )
    
    def __repr__(self) -> str:
        return f"<ThreatIntelligence(threat_id='{self.threat_id}', type='{self.threat_type}')>"


class ComplianceReport(BaseModel, TimestampMixin, TenantMixin):
    __tablename__ = "compliance_report"
    """
    Compliance reporting for privacy and security audits.
    
    Generates and stores compliance reports for various
    regulatory requirements (GDPR, CCPA, HIPAA, etc.).
    """
    
    # Report identification
    report_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        doc="Unique report identifier"
    )
    
    report_type = Column(
        String(50),
        nullable=False,
        doc="Type of compliance report"
    )
    
    regulation = Column(
        String(50),
        nullable=False,
        doc="Regulatory framework (GDPR, CCPA, etc.)"
    )
    
    # Report period
    period_start = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Report period start date"
    )
    
    period_end = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Report period end date"
    )
    
    # Report content
    summary = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Report summary and key metrics"
    )
    
    findings = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Compliance findings and issues"
    )
    
    recommendations = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Compliance recommendations"
    )
    
    # Report status
    status = Column(
        String(20),
        default="draft",
        nullable=False,
        doc="Report status (draft, final, submitted)"
    )
    
    compliance_score = Column(
        Float,
        nullable=True,
        doc="Overall compliance score (0.0 to 100.0)"
    )
    
    # Audit trail
    generated_by = Column(
        String(255),
        nullable=False,
        doc="User or system that generated the report"
    )
    
    reviewed_by = Column(
        String(255),
        nullable=True,
        doc="User who reviewed the report"
    )
    
    approved_by = Column(
        String(255),
        nullable=True,
        doc="User who approved the report"
    )
    
    # Additional metadata
    report_data = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Detailed report data and metrics"
    )
    
    attachments = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Report attachments and supporting documents"
    )
    
    def __repr__(self) -> str:
        return f"<ComplianceReport(report_id={self.report_id}, type='{self.report_type}')>"