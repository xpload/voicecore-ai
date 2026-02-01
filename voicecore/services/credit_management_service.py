"""
Credit Management Service for VoiceCore AI.

Implements configurable credit system per tenant, usage tracking,
and billing enforcement per Requirement 6.7.
"""

import uuid
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from sqlalchemy import select, and_, func, desc, update
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    CreditPlan, TenantSubscription, UsageRecord, CreditTransaction, 
    BillingAlert, Tenant, PlanType, UsageType, BillingStatus
)
from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


@dataclass
class UsageEvent:
    """Usage event for credit consumption."""
    tenant_id: uuid.UUID
    usage_type: UsageType
    quantity: Decimal
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CreditBalance:
    """Current credit balance information."""
    tenant_id: uuid.UUID
    credits_allocated: int
    credits_used: int
    credits_remaining: int
    rollover_credits: int
    overage_credits: int
    next_billing_date: datetime
    plan_name: str
    plan_type: str


@dataclass
class BillingPeriod:
    """Billing period information."""
    start_date: datetime
    end_date: datetime
    days_remaining: int
    is_current: bool


class CreditManagementService:
    """
    Comprehensive credit management and billing service.
    
    Implements configurable credit system per tenant with usage tracking,
    enforcement, and billing integration per Requirement 6.7.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Usage tracking cache
        self.usage_cache: Dict[str, List[UsageEvent]] = {}
        
        # Alert thresholds
        self.alert_thresholds = {
            "credit_low": 0.2,      # 20% remaining
            "credit_critical": 0.1,  # 10% remaining
            "overage": 1.0          # Any overage
        }
        
        # Background task for processing usage
        self.processing_usage = False
    
    async def get_tenant_subscription(
        self,
        tenant_id: uuid.UUID
    ) -> Optional[TenantSubscription]:
        """
        Get tenant's current subscription.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            TenantSubscription or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, tenant_id)
                
                query = select(TenantSubscription).where(
                    and_(
                        TenantSubscription.tenant_id == tenant_id,
                        TenantSubscription.status == BillingStatus.ACTIVE.value
                    )
                ).options(selectinload(TenantSubscription.credit_plan))
                
                result = await session.execute(query)
                return result.scalar_one_or_none()
                
        except Exception as e:
            self.logger.error("Failed to get tenant subscription", error=str(e))
            return None
    
    async def create_tenant_subscription(
        self,
        tenant_id: uuid.UUID,
        credit_plan_id: uuid.UUID,
        start_date: Optional[datetime] = None
    ) -> Optional[TenantSubscription]:
        """
        Create a new tenant subscription.
        
        Args:
            tenant_id: Tenant identifier
            credit_plan_id: Credit plan identifier
            start_date: Subscription start date (defaults to now)
            
        Returns:
            Created TenantSubscription or None if failed
        """
        try:
            if not start_date:
                start_date = datetime.utcnow()
            
            # Calculate billing period
            next_billing_date = start_date + timedelta(days=30)  # Monthly billing
            current_period_end = next_billing_date
            
            async with get_db_session() as session:
                await set_tenant_context(session, tenant_id)
                
                # Get credit plan
                plan_query = select(CreditPlan).where(CreditPlan.id == credit_plan_id)
                plan_result = await session.execute(plan_query)
                credit_plan = plan_result.scalar_one_or_none()
                
                if not credit_plan:
                    raise ValueError(f"Credit plan not found: {credit_plan_id}")
                
                # Create subscription
                subscription = TenantSubscription(
                    tenant_id=tenant_id,
                    credit_plan_id=credit_plan_id,
                    status=BillingStatus.ACTIVE.value,
                    started_at=start_date,
                    next_billing_date=next_billing_date,
                    current_period_start=start_date,
                    current_period_end=current_period_end,
                    credits_allocated=credit_plan.monthly_credits,
                    credits_used=0,
                    credits_remaining=credit_plan.monthly_credits
                )
                
                session.add(subscription)
                await session.commit()
                await session.refresh(subscription)
                
                # Create initial credit allocation transaction
                await self._create_credit_transaction(
                    session=session,
                    tenant_id=tenant_id,
                    subscription_id=subscription.id,
                    transaction_type="allocation",
                    credits_amount=credit_plan.monthly_credits,
                    balance_before=0,
                    balance_after=credit_plan.monthly_credits,
                    description=f"Monthly credit allocation for {credit_plan.name}",
                    billing_period_start=start_date,
                    billing_period_end=current_period_end
                )
                
                self.logger.info(
                    "Tenant subscription created",
                    tenant_id=str(tenant_id),
                    plan_name=credit_plan.name,
                    credits_allocated=credit_plan.monthly_credits
                )
                
                return subscription
                
        except Exception as e:
            self.logger.error("Failed to create tenant subscription", error=str(e))
            return None
    
    async def record_usage(
        self,
        usage_event: UsageEvent
    ) -> bool:
        """
        Record usage event and consume credits.
        
        Args:
            usage_event: Usage event to record
            
        Returns:
            True if usage was recorded successfully
        """
        try:
            # Get tenant subscription
            subscription = await self.get_tenant_subscription(usage_event.tenant_id)
            if not subscription:
                self.logger.warning(
                    "No active subscription found for usage",
                    tenant_id=str(usage_event.tenant_id)
                )
                return False
            
            # Calculate credits to consume
            usage_rates = subscription.credit_plan.usage_rates or {}
            unit_rate = Decimal(str(usage_rates.get(usage_event.usage_type.value, 1)))
            credits_to_consume = int(usage_event.quantity * unit_rate)
            
            if credits_to_consume <= 0:
                return True  # No credits needed
            
            async with get_db_session() as session:
                await set_tenant_context(session, usage_event.tenant_id)
                
                # Check if tenant has enough credits or allows overages
                current_balance = subscription.credits_remaining
                will_overage = credits_to_consume > current_balance
                
                # Create usage record
                usage_record = UsageRecord(
                    tenant_id=usage_event.tenant_id,
                    subscription_id=subscription.id,
                    usage_type=usage_event.usage_type.value,
                    quantity=usage_event.quantity,
                    credits_consumed=credits_to_consume,
                    unit_rate=unit_rate,
                    resource_id=usage_event.resource_id,
                    resource_type=usage_event.resource_type,
                    metadata=usage_event.metadata or {},
                    billing_period_start=subscription.current_period_start,
                    billing_period_end=subscription.current_period_end,
                    usage_timestamp=datetime.utcnow()
                )
                
                session.add(usage_record)
                
                # Update subscription credits
                new_credits_used = subscription.credits_used + credits_to_consume
                new_credits_remaining = max(0, subscription.credits_remaining - credits_to_consume)
                
                await session.execute(
                    update(TenantSubscription)
                    .where(TenantSubscription.id == subscription.id)
                    .values(
                        credits_used=new_credits_used,
                        credits_remaining=new_credits_remaining
                    )
                )
                
                # Create credit transaction
                await self._create_credit_transaction(
                    session=session,
                    tenant_id=usage_event.tenant_id,
                    subscription_id=subscription.id,
                    transaction_type="usage",
                    credits_amount=-credits_to_consume,
                    balance_before=current_balance,
                    balance_after=new_credits_remaining,
                    description=f"Usage: {usage_event.usage_type.value}",
                    reference_id=str(usage_record.id),
                    reference_type="usage_record",
                    billing_period_start=subscription.current_period_start,
                    billing_period_end=subscription.current_period_end
                )
                
                await session.commit()
                
                # Check for alerts
                if will_overage:
                    await self._create_overage_alert(
                        usage_event.tenant_id, subscription, credits_to_consume
                    )
                elif new_credits_remaining <= subscription.credits_allocated * self.alert_thresholds["credit_critical"]:
                    await self._create_low_credit_alert(
                        usage_event.tenant_id, subscription, "critical"
                    )
                elif new_credits_remaining <= subscription.credits_allocated * self.alert_thresholds["credit_low"]:
                    await self._create_low_credit_alert(
                        usage_event.tenant_id, subscription, "warning"
                    )
                
                self.logger.info(
                    "Usage recorded",
                    tenant_id=str(usage_event.tenant_id),
                    usage_type=usage_event.usage_type.value,
                    credits_consumed=credits_to_consume,
                    credits_remaining=new_credits_remaining
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to record usage", error=str(e))
            return False
    
    async def get_credit_balance(
        self,
        tenant_id: uuid.UUID
    ) -> Optional[CreditBalance]:
        """
        Get current credit balance for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            CreditBalance or None if not found
        """
        try:
            subscription = await self.get_tenant_subscription(tenant_id)
            if not subscription:
                return None
            
            # Calculate overage credits
            overage_credits = max(0, subscription.credits_used - subscription.credits_allocated)
            
            return CreditBalance(
                tenant_id=tenant_id,
                credits_allocated=subscription.credits_allocated,
                credits_used=subscription.credits_used,
                credits_remaining=subscription.credits_remaining,
                rollover_credits=subscription.rollover_credits,
                overage_credits=overage_credits,
                next_billing_date=subscription.next_billing_date,
                plan_name=subscription.credit_plan.name,
                plan_type=subscription.credit_plan.plan_type
            )
            
        except Exception as e:
            self.logger.error("Failed to get credit balance", error=str(e))
            return None
    
    async def check_usage_limits(
        self,
        tenant_id: uuid.UUID,
        usage_type: UsageType,
        requested_quantity: Decimal
    ) -> Tuple[bool, str]:
        """
        Check if usage is within limits.
        
        Args:
            tenant_id: Tenant identifier
            usage_type: Type of usage
            requested_quantity: Requested usage quantity
            
        Returns:
            Tuple of (allowed, reason)
        """
        try:
            subscription = await self.get_tenant_subscription(tenant_id)
            if not subscription:
                return False, "No active subscription"
            
            # Check plan limits
            usage_limits = subscription.credit_plan.usage_limits or {}
            usage_rates = subscription.credit_plan.usage_rates or {}
            
            # Get current period usage for this type
            current_usage = await self._get_current_period_usage(
                tenant_id, usage_type, subscription
            )
            
            # Check quantity limit
            limit = usage_limits.get(usage_type.value)
            if limit and (current_usage + requested_quantity) > limit:
                return False, f"Usage limit exceeded for {usage_type.value}"
            
            # Check credit limit
            unit_rate = Decimal(str(usage_rates.get(usage_type.value, 1)))
            credits_needed = int(requested_quantity * unit_rate)
            
            if credits_needed > subscription.credits_remaining:
                # Check if overages are allowed
                overage_rate = subscription.credit_plan.overage_rate
                if overage_rate <= 0:
                    return False, "Insufficient credits and overages not allowed"
                else:
                    return True, f"Will incur overage charges at ${overage_rate} per credit"
            
            return True, "Usage allowed"
            
        except Exception as e:
            self.logger.error("Failed to check usage limits", error=str(e))
            return False, "Error checking limits"
    
    async def get_usage_summary(
        self,
        tenant_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary for tenant.
        
        Args:
            tenant_id: Tenant identifier
            start_date: Start date for summary (defaults to current period)
            end_date: End date for summary (defaults to current period)
            
        Returns:
            Usage summary dictionary
        """
        try:
            subscription = await self.get_tenant_subscription(tenant_id)
            if not subscription:
                return {}
            
            # Use current billing period if dates not provided
            if not start_date:
                start_date = subscription.current_period_start
            if not end_date:
                end_date = subscription.current_period_end
            
            async with get_db_session() as session:
                await set_tenant_context(session, tenant_id)
                
                # Get usage by type
                usage_query = select(
                    UsageRecord.usage_type,
                    func.sum(UsageRecord.quantity).label("total_quantity"),
                    func.sum(UsageRecord.credits_consumed).label("total_credits"),
                    func.count(UsageRecord.id).label("usage_count")
                ).where(
                    and_(
                        UsageRecord.tenant_id == tenant_id,
                        UsageRecord.usage_timestamp >= start_date,
                        UsageRecord.usage_timestamp <= end_date
                    )
                ).group_by(UsageRecord.usage_type)
                
                result = await session.execute(usage_query)
                usage_by_type = {
                    row.usage_type: {
                        "quantity": float(row.total_quantity),
                        "credits": row.total_credits,
                        "count": row.usage_count
                    }
                    for row in result
                }
                
                # Get total usage
                total_credits_used = sum(
                    usage["credits"] for usage in usage_by_type.values()
                )
                
                return {
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                        "days": (end_date - start_date).days
                    },
                    "credits": {
                        "allocated": subscription.credits_allocated,
                        "used": total_credits_used,
                        "remaining": subscription.credits_remaining,
                        "rollover": subscription.rollover_credits
                    },
                    "usage_by_type": usage_by_type,
                    "plan": {
                        "name": subscription.credit_plan.name,
                        "type": subscription.credit_plan.plan_type
                    }
                }
                
        except Exception as e:
            self.logger.error("Failed to get usage summary", error=str(e))
            return {}
    
    async def process_billing_cycle(
        self,
        tenant_id: uuid.UUID
    ) -> bool:
        """
        Process billing cycle for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            True if billing cycle processed successfully
        """
        try:
            subscription = await self.get_tenant_subscription(tenant_id)
            if not subscription:
                return False
            
            # Check if billing cycle is due
            if datetime.utcnow() < subscription.next_billing_date:
                return True  # Not due yet
            
            async with get_db_session() as session:
                await set_tenant_context(session, tenant_id)
                
                # Calculate new billing period
                new_period_start = subscription.next_billing_date
                new_period_end = new_period_start + timedelta(days=30)
                new_billing_date = new_period_end
                
                # Handle rollover credits
                rollover_credits = 0
                if subscription.credit_plan.rollover_enabled:
                    max_rollover = subscription.credit_plan.max_rollover_credits
                    rollover_credits = min(subscription.credits_remaining, max_rollover)
                
                # Allocate new credits
                new_credits_allocated = subscription.credit_plan.monthly_credits + rollover_credits
                
                # Update subscription
                await session.execute(
                    update(TenantSubscription)
                    .where(TenantSubscription.id == subscription.id)
                    .values(
                        current_period_start=new_period_start,
                        current_period_end=new_period_end,
                        next_billing_date=new_billing_date,
                        credits_allocated=new_credits_allocated,
                        credits_used=0,
                        credits_remaining=new_credits_allocated,
                        rollover_credits=rollover_credits
                    )
                )
                
                # Create credit allocation transaction
                await self._create_credit_transaction(
                    session=session,
                    tenant_id=tenant_id,
                    subscription_id=subscription.id,
                    transaction_type="allocation",
                    credits_amount=new_credits_allocated,
                    balance_before=0,
                    balance_after=new_credits_allocated,
                    description=f"Monthly credit allocation with {rollover_credits} rollover credits",
                    billing_period_start=new_period_start,
                    billing_period_end=new_period_end
                )
                
                await session.commit()
                
                self.logger.info(
                    "Billing cycle processed",
                    tenant_id=str(tenant_id),
                    new_credits=new_credits_allocated,
                    rollover_credits=rollover_credits
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to process billing cycle", error=str(e))
            return False
    
    # Private helper methods
    
    async def _create_credit_transaction(
        self,
        session,
        tenant_id: uuid.UUID,
        subscription_id: uuid.UUID,
        transaction_type: str,
        credits_amount: int,
        balance_before: int,
        balance_after: int,
        description: str,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        billing_period_start: Optional[datetime] = None,
        billing_period_end: Optional[datetime] = None
    ):
        """Create a credit transaction record."""
        transaction = CreditTransaction(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            transaction_type=transaction_type,
            credits_amount=credits_amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end
        )
        
        session.add(transaction)
    
    async def _get_current_period_usage(
        self,
        tenant_id: uuid.UUID,
        usage_type: UsageType,
        subscription: TenantSubscription
    ) -> Decimal:
        """Get current period usage for specific type."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, tenant_id)
                
                query = select(func.sum(UsageRecord.quantity)).where(
                    and_(
                        UsageRecord.tenant_id == tenant_id,
                        UsageRecord.usage_type == usage_type.value,
                        UsageRecord.usage_timestamp >= subscription.current_period_start,
                        UsageRecord.usage_timestamp <= subscription.current_period_end
                    )
                )
                
                result = await session.execute(query)
                total = result.scalar()
                return Decimal(str(total or 0))
                
        except Exception as e:
            self.logger.error("Failed to get current period usage", error=str(e))
            return Decimal("0")
    
    async def _create_overage_alert(
        self,
        tenant_id: uuid.UUID,
        subscription: TenantSubscription,
        overage_credits: int
    ):
        """Create overage alert."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, tenant_id)
                
                alert = BillingAlert(
                    tenant_id=tenant_id,
                    subscription_id=subscription.id,
                    alert_type="overage",
                    severity="warning",
                    title="Credit Overage Detected",
                    message=f"Your account has exceeded the credit limit by {overage_credits} credits. "
                           f"Overage charges will apply at ${subscription.credit_plan.overage_rate} per credit.",
                    threshold_type="absolute",
                    threshold_value=Decimal(str(subscription.credits_allocated)),
                    current_value=Decimal(str(subscription.credits_used + overage_credits))
                )
                
                session.add(alert)
                await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to create overage alert", error=str(e))
    
    async def _create_low_credit_alert(
        self,
        tenant_id: uuid.UUID,
        subscription: TenantSubscription,
        severity: str
    ):
        """Create low credit alert."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, tenant_id)
                
                percentage_remaining = (subscription.credits_remaining / subscription.credits_allocated) * 100
                
                alert = BillingAlert(
                    tenant_id=tenant_id,
                    subscription_id=subscription.id,
                    alert_type="credit_low",
                    severity=severity,
                    title=f"Low Credit Balance - {percentage_remaining:.1f}% Remaining",
                    message=f"Your account has {subscription.credits_remaining} credits remaining "
                           f"({percentage_remaining:.1f}% of monthly allocation). "
                           f"Consider upgrading your plan or monitoring usage.",
                    threshold_type="percentage",
                    threshold_value=Decimal(str(self.alert_thresholds["credit_low"] * 100)),
                    current_value=Decimal(str(percentage_remaining))
                )
                
                session.add(alert)
                await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to create low credit alert", error=str(e))


# Global service instance
credit_management_service = CreditManagementService()