"""
Billing and Credit System Models for VoiceCore AI.

Implements configurable credit system per tenant plan
per Requirement 6.7.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, 
    ForeignKey, Numeric, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from voicecore.models.base import BaseModel


class CreditPlan(BaseModel):
    """
    Credit plan configuration for tenants.
    
    Defines the credit allocation, pricing, and limits
    for different tenant subscription plans.
    """
    __tablename__ = "credit_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Credit allocation
    monthly_credits = Column(Integer, nullable=False, default=0)
    overage_rate = Column(Numeric(10, 4), nullable=False, default=Decimal('0.0'))  # Cost per credit over limit
    
    # Feature limits
    max_agents = Column(Integer, nullable=False, default=10)
    max_concurrent_calls = Column(Integer, nullable=False, default=5)
    max_storage_gb = Column(Integer, nullable=False, default=1)
    
    # Feature flags
    features = Column(JSON, nullable=False, default=dict)  # {"ai_training": True, "analytics": True, etc.}
    
    # Pricing
    monthly_price = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))
    setup_fee = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant_subscriptions = relationship("TenantSubscription", back_populates="credit_plan")
    
    def __repr__(self):
        return f"<CreditPlan(id={self.id}, name='{self.name}', monthly_credits={self.monthly_credits})>"


class TenantSubscription(BaseModel):
    """
    Tenant subscription to a credit plan.
    
    Links tenants to their credit plans and tracks
    subscription status and billing information.
    """
    __tablename__ = "tenant_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    credit_plan_id = Column(UUID(as_uuid=True), ForeignKey("credit_plans.id"), nullable=False)
    
    # Subscription details
    status = Column(String(20), nullable=False, default="active")  # active, suspended, cancelled
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ends_at = Column(DateTime)  # NULL for ongoing subscriptions
    
    # Billing cycle
    billing_cycle = Column(String(20), nullable=False, default="monthly")  # monthly, yearly
    next_billing_date = Column(DateTime, nullable=False)
    
    # Custom overrides
    custom_monthly_credits = Column(Integer)  # Override plan default
    custom_overage_rate = Column(Numeric(10, 4))  # Override plan default
    custom_features = Column(JSON)  # Override plan features
    
    # Payment information
    payment_method_id = Column(String(100))  # External payment method reference
    billing_email = Column(String(255))
    
    # Status tracking
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="subscription")
    credit_plan = relationship("CreditPlan", back_populates="tenant_subscriptions")
    usage_records = relationship("CreditUsage", back_populates="subscription")
    invoices = relationship("Invoice", back_populates="subscription")
    
    # Indexes
    __table_args__ = (
        Index("idx_tenant_subscription_tenant", "tenant_id"),
        Index("idx_tenant_subscription_status", "status"),
        Index("idx_tenant_subscription_billing", "next_billing_date"),
    )
    
    @property
    def effective_monthly_credits(self) -> int:
        """Get effective monthly credits (custom or plan default)."""
        return self.custom_monthly_credits or self.credit_plan.monthly_credits
    
    @property
    def effective_overage_rate(self) -> Decimal:
        """Get effective overage rate (custom or plan default)."""
        return self.custom_overage_rate or self.credit_plan.overage_rate
    
    @property
    def effective_features(self) -> Dict[str, Any]:
        """Get effective features (custom or plan default)."""
        features = self.credit_plan.features.copy()
        if self.custom_features:
            features.update(self.custom_features)
        return features
    
    def __repr__(self):
        return f"<TenantSubscription(id={self.id}, tenant_id={self.tenant_id}, status='{self.status}')>"


class CreditUsage(BaseModel):
    """
    Credit usage tracking for tenants.
    
    Records credit consumption for billing and
    enforcement purposes.
    """
    __tablename__ = "credit_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("tenant_subscriptions.id"), nullable=False)
    
    # Usage details
    usage_type = Column(String(50), nullable=False)  # call_minute, ai_request, storage_gb, etc.
    quantity = Column(Integer, nullable=False, default=1)
    credits_consumed = Column(Integer, nullable=False, default=1)
    
    # Cost calculation
    unit_cost = Column(Numeric(10, 4), nullable=False, default=Decimal('0.0'))
    total_cost = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))
    
    # Reference information
    resource_id = Column(String(100))  # Call ID, Agent ID, etc.
    resource_type = Column(String(50))  # call, agent, storage, etc.
    
    # Metadata
    metadata = Column(JSON)  # Additional usage context
    
    # Timestamps
    usage_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    subscription = relationship("TenantSubscription", back_populates="usage_records")
    
    # Indexes
    __table_args__ = (
        Index("idx_credit_usage_tenant", "tenant_id"),
        Index("idx_credit_usage_subscription", "subscription_id"),
        Index("idx_credit_usage_date", "usage_date"),
        Index("idx_credit_usage_type", "usage_type"),
    )
    
    def __repr__(self):
        return f"<CreditUsage(id={self.id}, tenant_id={self.tenant_id}, credits={self.credits_consumed})>"


class CreditBalance(BaseModel):
    """
    Current credit balance for tenants.
    
    Tracks available credits and usage for the current
    billing period.
    """
    __tablename__ = "credit_balances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("tenant_subscriptions.id"), nullable=False)
    
    # Credit tracking
    allocated_credits = Column(Integer, nullable=False, default=0)
    used_credits = Column(Integer, nullable=False, default=0)
    remaining_credits = Column(Integer, nullable=False, default=0)
    
    # Overage tracking
    overage_credits = Column(Integer, nullable=False, default=0)
    overage_cost = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))
    
    # Billing period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Status
    is_suspended = Column(Boolean, nullable=False, default=False)
    suspension_reason = Column(String(100))
    
    # Timestamps
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    subscription = relationship("TenantSubscription")
    
    # Indexes
    __table_args__ = (
        Index("idx_credit_balance_tenant", "tenant_id"),
        Index("idx_credit_balance_period", "period_start", "period_end"),
    )
    
    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage of allocated credits."""
        if self.allocated_credits == 0:
            return 0.0
        return (self.used_credits / self.allocated_credits) * 100
    
    @property
    def is_over_limit(self) -> bool:
        """Check if tenant is over their credit limit."""
        return self.used_credits > self.allocated_credits
    
    def __repr__(self):
        return f"<CreditBalance(tenant_id={self.tenant_id}, remaining={self.remaining_credits})>"


class Invoice(BaseModel):
    """
    Billing invoices for tenant subscriptions.
    
    Generates and tracks invoices for subscription
    fees and overage charges.
    """
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("tenant_subscriptions.id"), nullable=False)
    
    # Invoice details
    invoice_number = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, paid, overdue, cancelled
    
    # Billing period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Amounts
    subscription_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))
    overage_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))
    tax_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))
    total_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))
    
    # Payment tracking
    paid_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))
    payment_date = Column(DateTime)
    payment_method = Column(String(50))
    payment_reference = Column(String(100))
    
    # Dates
    issued_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    
    # Invoice data
    line_items = Column(JSON)  # Detailed breakdown of charges
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    subscription = relationship("TenantSubscription", back_populates="invoices")
    
    # Indexes
    __table_args__ = (
        Index("idx_invoice_tenant", "tenant_id"),
        Index("idx_invoice_subscription", "subscription_id"),
        Index("idx_invoice_status", "status"),
        Index("idx_invoice_due_date", "due_date"),
    )
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return self.status == "pending" and self.due_date < datetime.utcnow()
    
    @property
    def outstanding_amount(self) -> Decimal:
        """Calculate outstanding amount."""
        return self.total_amount - self.paid_amount
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, number='{self.invoice_number}', total={self.total_amount})>"


class PaymentTransaction(BaseModel):
    """
    Payment transaction records.
    
    Tracks all payment transactions for audit
    and reconciliation purposes.
    """
    __tablename__ = "payment_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"))
    
    # Transaction details
    transaction_id = Column(String(100), nullable=False, unique=True)
    payment_processor = Column(String(50), nullable=False)  # stripe, paypal, etc.
    
    # Amount and currency
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    # Status
    status = Column(String(20), nullable=False)  # pending, completed, failed, refunded
    failure_reason = Column(String(255))
    
    # Payment method
    payment_method_type = Column(String(50))  # card, bank_transfer, etc.
    payment_method_details = Column(JSON)  # Masked payment details
    
    # Processor response
    processor_response = Column(JSON)
    
    # Timestamps
    processed_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    invoice = relationship("Invoice")
    
    # Indexes
    __table_args__ = (
        Index("idx_payment_transaction_tenant", "tenant_id"),
        Index("idx_payment_transaction_invoice", "invoice_id"),
        Index("idx_payment_transaction_status", "status"),
        Index("idx_payment_transaction_processor", "payment_processor"),
    )
    
    def __repr__(self):
        return f"<PaymentTransaction(id={self.id}, amount={self.amount}, status='{self.status}')>"


class CreditAlert(BaseModel):
    """
    Credit usage alerts and notifications.
    
    Tracks alerts sent to tenants about credit
    usage and billing issues.
    """
    __tablename__ = "credit_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # usage_warning, limit_exceeded, payment_failed, etc.
    severity = Column(String(20), nullable=False, default="info")  # info, warning, critical
    
    # Message
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Thresholds
    threshold_percentage = Column(Integer)  # Usage percentage that triggered alert
    current_usage = Column(Integer)
    credit_limit = Column(Integer)
    
    # Status
    is_acknowledged = Column(Boolean, nullable=False, default=False)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(100))
    
    # Delivery
    delivery_methods = Column(JSON)  # ["email", "webhook", "dashboard"]
    delivery_status = Column(JSON)  # Delivery confirmation per method
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    
    # Indexes
    __table_args__ = (
        Index("idx_credit_alert_tenant", "tenant_id"),
        Index("idx_credit_alert_type", "alert_type"),
        Index("idx_credit_alert_severity", "severity"),
        Index("idx_credit_alert_acknowledged", "is_acknowledged"),
    )
    
    def __repr__(self):
        return f"<CreditAlert(id={self.id}, tenant_id={self.tenant_id}, type='{self.alert_type}')>"