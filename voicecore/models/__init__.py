"""
VoiceCore AI Database Models.

This module exports all database models for the VoiceCore AI system,
providing a centralized import location for all model classes.
"""

from .base import Base, BaseModel, TimestampMixin, TenantMixin, SoftDeleteMixin, AuditMixin

# Tenant and configuration models
from .tenant import Tenant, TenantSettings

# Agent and department models
from .agent import Agent, Department, AgentSession, AgentStatus

# Call and communication models
from .call import Call, CallEvent, CallQueue, CallStatus, CallDirection, CallType

# Knowledge base and spam detection models
from .knowledge import (
    KnowledgeBase, 
    SpamRule, 
    SpamReport, 
    KnowledgeCategory
)

# Voicemail models
from .voicemail import (
    VoicemailBox,
    VoicemailMessage,
    VoicemailNotification,
    VoicemailStatus,
    VoicemailPriority
)

# Analytics and metrics models
from .analytics import (
    CallAnalytics,
    AgentMetrics,
    SystemMetrics,
    ReportTemplate,
    MetricType
)

# VIP caller management models
from .vip import (
    VIPCaller,
    VIPCallHistory,
    VIPEscalationRule,
    VIPPriority,
    VIPStatus,
    VIPHandlingRule
)

# Callback request models
from .callback import (
    CallbackRequest,
    CallbackSchedule,
    CallbackAttempt,
    CallbackStatus,
    CallbackPriority,
    CallbackType
)

# Billing and credit system models
from .billing import (
    CreditPlan,
    TenantSubscription,
    UsageRecord,
    CreditTransaction,
    BillingAlert,
    PlanType,
    UsageType,
    BillingStatus
)

# Export all models for easy importing
__all__ = [
    # Base classes
    "Base",
    "BaseModel", 
    "TimestampMixin",
    "TenantMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    
    # Tenant models
    "Tenant",
    "TenantSettings",
    
    # Agent models
    "Agent",
    "Department", 
    "AgentSession",
    "AgentStatus",
    
    # Call models
    "Call",
    "CallEvent",
    "CallQueue",
    "CallStatus",
    "CallDirection", 
    "CallType",
    
    # Knowledge models
    "KnowledgeBase",
    "SpamRule",
    "SpamReport",
    "KnowledgeCategory",
    
    # Voicemail models
    "VoicemailBox",
    "VoicemailMessage", 
    "VoicemailNotification",
    "VoicemailStatus",
    "VoicemailPriority",
    
    # Analytics models
    "CallAnalytics",
    "AgentMetrics", 
    "SystemMetrics",
    "ReportTemplate",
    "MetricType",
    
    # VIP models
    "VIPCaller",
    "VIPCallHistory",
    "VIPEscalationRule",
    "VIPPriority",
    "VIPStatus",
    "VIPHandlingRule",
    
    # Callback models
    "CallbackRequest",
    "CallbackSchedule",
    "CallbackAttempt",
    "CallbackStatus",
    "CallbackPriority",
    "CallbackType",
    
    # Billing models
    "CreditPlan",
    "TenantSubscription",
    "UsageRecord",
    "CreditTransaction",
    "BillingAlert",
    "PlanType",
    "UsageType",
    "BillingStatus",
]