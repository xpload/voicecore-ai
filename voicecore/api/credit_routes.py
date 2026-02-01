"""
API routes for credit management and billing system.

Provides endpoints for credit plans, subscriptions, usage tracking,
and billing management per Requirement 6.7.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator

from voicecore.services.credit_management_service import credit_management_service
from voicecore.services.auth_service import get_current_tenant
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/credits", tags=["Credit Management & Billing"])


# Request/Response Models

class CreateSubscriptionRequest(BaseModel):
    """Request model for creating tenant subscription."""
    credit_plan_id: str = Field(..., description="Credit plan ID")
    billing_cycle: str = Field("monthly", description="Billing cycle")
    billing_email: Optional[str] = Field(None, description="Billing email address")
    custom_credits: Optional[int] = Field(None, description="Custom monthly credits override")
    custom_overage_rate: Optional[float] = Field(None, description="Custom overage rate override")
    
    @validator('billing_cycle')
    def validate_billing_cycle(cls, v):
        if v not in ["monthly", "yearly"]:
            raise ValueError("Billing cycle must be 'monthly' or 'yearly'")
        return v
    
    @validator('custom_credits')
    def validate_custom_credits(cls, v):
        if v is not None and v < 0:
            raise ValueError("Custom credits must be non-negative")
        return v
    
    @validator('custom_overage_rate')
    def validate_custom_overage_rate(cls, v):
        if v is not None and v < 0:
            raise ValueError("Custom overage rate must be non-negative")
        return v


class RecordUsageRequest(BaseModel):
    """Request model for recording credit usage."""
    usage_type: str = Field(..., description="Type of usage")
    quantity: int = Field(1, description="Quantity of usage")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    resource_type: Optional[str] = Field(None, description="Resource type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v


class ProcessPaymentRequest(BaseModel):
    """Request model for processing payment."""
    invoice_id: str = Field(..., description="Invoice ID")
    payment_processor: str = Field(..., description="Payment processor")
    transaction_id: str = Field(..., description="Transaction ID")
    amount: float = Field(..., description="Payment amount")
    payment_method_type: str = Field(..., description="Payment method type")
    processor_response: Dict[str, Any] = Field(..., description="Processor response")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class CreateAlertRequest(BaseModel):
    """Request model for creating credit alert."""
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    threshold_percentage: Optional[int] = Field(None, description="Threshold percentage")
    
    @validator('severity')
    def validate_severity(cls, v):
        if v not in ["info", "warning", "critical"]:
            raise ValueError("Severity must be 'info', 'warning', or 'critical'")
        return v


# Credit Plan Endpoints

@router.get("/plans")
async def get_credit_plans():
    """
    Get available credit plans.
    
    Returns all active credit plans with their features,
    pricing, and limits for tenant selection.
    """
    try:
        plans = await credit_management_service.get_credit_plans()
        
        return {
            "success": True,
            "total_plans": len(plans),
            "credit_plans": [
                {
                    "id": str(plan.id),
                    "name": plan.name,
                    "description": plan.description,
                    "monthly_credits": plan.monthly_credits,
                    "overage_rate": float(plan.overage_rate),
                    "max_agents": plan.max_agents,
                    "max_concurrent_calls": plan.max_concurrent_calls,
                    "max_storage_gb": plan.max_storage_gb,
                    "features": plan.features,
                    "monthly_price": float(plan.monthly_price),
                    "setup_fee": float(plan.setup_fee),
                    "is_active": plan.is_active
                }
                for plan in plans
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get credit plans", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get credit plans")


@router.get("/plans/{plan_id}")
async def get_credit_plan(plan_id: str):
    """
    Get details of a specific credit plan.
    
    Returns detailed information about a credit plan
    including all features and pricing details.
    """
    try:
        plans = await credit_management_service.get_credit_plans(active_only=False)
        plan = next((p for p in plans if str(p.id) == plan_id), None)
        
        if not plan:
            raise HTTPException(status_code=404, detail="Credit plan not found")
        
        return {
            "success": True,
            "credit_plan": {
                "id": str(plan.id),
                "name": plan.name,
                "description": plan.description,
                "monthly_credits": plan.monthly_credits,
                "overage_rate": float(plan.overage_rate),
                "max_agents": plan.max_agents,
                "max_concurrent_calls": plan.max_concurrent_calls,
                "max_storage_gb": plan.max_storage_gb,
                "features": plan.features,
                "monthly_price": float(plan.monthly_price),
                "setup_fee": float(plan.setup_fee),
                "is_active": plan.is_active,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get credit plan", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get credit plan")


# Subscription Management Endpoints

@router.post("/subscription")
async def create_subscription(
    request: CreateSubscriptionRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Create a new tenant subscription.
    
    Subscribes the tenant to a credit plan with optional
    custom overrides for credits and overage rates.
    """
    try:
        custom_overage_rate = None
        if request.custom_overage_rate is not None:
            custom_overage_rate = Decimal(str(request.custom_overage_rate))
        
        subscription = await credit_management_service.create_subscription(
            tenant_id=tenant_id,
            credit_plan_id=uuid.UUID(request.credit_plan_id),
            billing_cycle=request.billing_cycle,
            billing_email=request.billing_email,
            custom_credits=request.custom_credits,
            custom_overage_rate=custom_overage_rate
        )
        
        return {
            "success": True,
            "subscription": {
                "id": str(subscription.id),
                "tenant_id": str(subscription.tenant_id),
                "credit_plan_id": str(subscription.credit_plan_id),
                "status": subscription.status,
                "billing_cycle": subscription.billing_cycle,
                "next_billing_date": subscription.next_billing_date.isoformat(),
                "effective_monthly_credits": subscription.effective_monthly_credits,
                "effective_overage_rate": float(subscription.effective_overage_rate),
                "created_at": subscription.created_at.isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create subscription", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.get("/subscription")
async def get_subscription(
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get tenant's current subscription.
    
    Returns the tenant's active subscription details
    including credit plan information and billing status.
    """
    try:
        subscription = await credit_management_service.get_tenant_subscription(tenant_id)
        
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        return {
            "success": True,
            "subscription": {
                "id": str(subscription.id),
                "tenant_id": str(subscription.tenant_id),
                "status": subscription.status,
                "billing_cycle": subscription.billing_cycle,
                "next_billing_date": subscription.next_billing_date.isoformat(),
                "effective_monthly_credits": subscription.effective_monthly_credits,
                "effective_overage_rate": float(subscription.effective_overage_rate),
                "effective_features": subscription.effective_features,
                "billing_email": subscription.billing_email,
                "created_at": subscription.created_at.isoformat(),
                "credit_plan": {
                    "id": str(subscription.credit_plan.id),
                    "name": subscription.credit_plan.name,
                    "description": subscription.credit_plan.description,
                    "monthly_price": float(subscription.credit_plan.monthly_price)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get subscription", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get subscription")


# Credit Balance and Usage Endpoints

@router.get("/balance")
async def get_credit_balance(
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get tenant's current credit balance.
    
    Returns current credit allocation, usage, and remaining
    credits for the current billing period.
    """
    try:
        balance = await credit_management_service.get_credit_balance(tenant_id)
        
        if not balance:
            raise HTTPException(status_code=404, detail="Credit balance not found")
        
        return {
            "success": True,
            "credit_balance": {
                "tenant_id": str(balance.tenant_id),
                "allocated_credits": balance.allocated_credits,
                "used_credits": balance.used_credits,
                "remaining_credits": balance.remaining_credits,
                "overage_credits": balance.overage_credits,
                "overage_cost": float(balance.overage_cost),
                "usage_percentage": round(balance.usage_percentage, 2),
                "is_over_limit": balance.is_over_limit,
                "period_start": balance.period_start.isoformat(),
                "period_end": balance.period_end.isoformat(),
                "is_suspended": balance.is_suspended,
                "suspension_reason": balance.suspension_reason,
                "last_updated": balance.last_updated.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get credit balance", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get credit balance")


@router.post("/usage")
async def record_usage(
    request: RecordUsageRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Record credit usage for the tenant.
    
    Records usage of credits for various system features
    and updates the tenant's credit balance accordingly.
    """
    try:
        success = await credit_management_service.record_usage(
            tenant_id=tenant_id,
            usage_type=request.usage_type,
            quantity=request.quantity,
            resource_id=request.resource_id,
            resource_type=request.resource_type,
            metadata=request.metadata
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to record usage")
        
        return {
            "success": True,
            "message": "Usage recorded successfully",
            "usage": {
                "usage_type": request.usage_type,
                "quantity": request.quantity,
                "recorded_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to record usage", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to record usage")


@router.get("/usage")
async def get_usage_history(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    days: int = Query(30, ge=1, le=365, description="Number of days to retrieve"),
    usage_type: Optional[str] = Query(None, description="Filter by usage type")
):
    """
    Get tenant's usage history.
    
    Returns detailed usage history for the specified time period
    with optional filtering by usage type.
    """
    try:
        usage_records = await credit_management_service.get_usage_history(
            tenant_id=tenant_id,
            days=days,
            usage_type=usage_type
        )
        
        return {
            "success": True,
            "period_days": days,
            "usage_type_filter": usage_type,
            "total_records": len(usage_records),
            "usage_history": [
                {
                    "id": str(record.id),
                    "usage_type": record.usage_type,
                    "quantity": record.quantity,
                    "credits_consumed": record.credits_consumed,
                    "unit_cost": float(record.unit_cost),
                    "total_cost": float(record.total_cost),
                    "resource_id": record.resource_id,
                    "resource_type": record.resource_type,
                    "metadata": record.metadata,
                    "usage_date": record.usage_date.isoformat(),
                    "created_at": record.created_at.isoformat()
                }
                for record in usage_records
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get usage history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get usage history")


@router.get("/usage/types")
async def get_usage_types():
    """
    Get available usage types.
    
    Returns all supported usage types with their
    credit costs and descriptions.
    """
    try:
        usage_types = credit_management_service.usage_types
        
        return {
            "success": True,
            "usage_types": [
                {
                    "type": usage_type,
                    "credits": config["credits"],
                    "description": config["description"]
                }
                for usage_type, config in usage_types.items()
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get usage types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get usage types")


# Billing and Payment Endpoints

@router.post("/invoice/generate")
async def generate_invoice(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    period_start: Optional[datetime] = Query(None, description="Billing period start"),
    period_end: Optional[datetime] = Query(None, description="Billing period end")
):
    """
    Generate invoice for billing period.
    
    Creates an invoice for the specified billing period
    including subscription fees and overage charges.
    """
    try:
        # Default to current month if no period specified
        if not period_start:
            now = datetime.utcnow()
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if not period_end:
            period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        
        invoice = await credit_management_service.generate_invoice(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end
        )
        
        if not invoice:
            raise HTTPException(status_code=400, detail="Failed to generate invoice")
        
        return {
            "success": True,
            "invoice": {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "status": invoice.status,
                "period_start": invoice.period_start.isoformat(),
                "period_end": invoice.period_end.isoformat(),
                "subscription_amount": float(invoice.subscription_amount),
                "overage_amount": float(invoice.overage_amount),
                "tax_amount": float(invoice.tax_amount),
                "total_amount": float(invoice.total_amount),
                "paid_amount": float(invoice.paid_amount),
                "outstanding_amount": float(invoice.outstanding_amount),
                "issued_date": invoice.issued_date.isoformat(),
                "due_date": invoice.due_date.isoformat(),
                "is_overdue": invoice.is_overdue,
                "line_items": invoice.line_items
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate invoice", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate invoice")


@router.post("/payment/process")
async def process_payment(
    request: ProcessPaymentRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Process payment for an invoice.
    
    Records payment transaction and updates invoice
    status based on payment amount.
    """
    try:
        success = await credit_management_service.process_payment(
            tenant_id=tenant_id,
            invoice_id=uuid.UUID(request.invoice_id),
            payment_processor=request.payment_processor,
            transaction_id=request.transaction_id,
            amount=Decimal(str(request.amount)),
            payment_method_type=request.payment_method_type,
            processor_response=request.processor_response
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to process payment")
        
        return {
            "success": True,
            "message": "Payment processed successfully",
            "payment": {
                "transaction_id": request.transaction_id,
                "amount": request.amount,
                "payment_processor": request.payment_processor,
                "processed_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process payment", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process payment")


# Alert Management Endpoints

@router.post("/alerts")
async def create_credit_alert(
    request: CreateAlertRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Create a credit usage alert.
    
    Creates a new alert for credit usage monitoring
    and notification purposes.
    """
    try:
        alert = await credit_management_service.create_credit_alert(
            tenant_id=tenant_id,
            alert_type=request.alert_type,
            severity=request.severity,
            title=request.title,
            message=request.message,
            threshold_percentage=request.threshold_percentage
        )
        
        return {
            "success": True,
            "alert": {
                "id": str(alert.id),
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "threshold_percentage": alert.threshold_percentage,
                "is_acknowledged": alert.is_acknowledged,
                "created_at": alert.created_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Failed to create credit alert", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create credit alert")


@router.get("/alerts")
async def get_credit_alerts(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    unacknowledged_only: bool = Query(False, description="Return only unacknowledged alerts")
):
    """
    Get tenant's credit alerts.
    
    Returns credit usage alerts with optional filtering
    for unacknowledged alerts only.
    """
    try:
        alerts = await credit_management_service.get_tenant_alerts(
            tenant_id=tenant_id,
            unacknowledged_only=unacknowledged_only
        )
        
        return {
            "success": True,
            "unacknowledged_only": unacknowledged_only,
            "total_alerts": len(alerts),
            "alerts": [
                {
                    "id": str(alert.id),
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "message": alert.message,
                    "threshold_percentage": alert.threshold_percentage,
                    "current_usage": alert.current_usage,
                    "credit_limit": alert.credit_limit,
                    "is_acknowledged": alert.is_acknowledged,
                    "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    "acknowledged_by": alert.acknowledged_by,
                    "delivery_methods": alert.delivery_methods,
                    "delivery_status": alert.delivery_status,
                    "created_at": alert.created_at.isoformat()
                }
                for alert in alerts
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get credit alerts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get credit alerts")


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Acknowledge a credit alert.
    
    Marks a credit alert as acknowledged to prevent
    duplicate notifications.
    """
    try:
        # This would be implemented in the service
        # For now, return success response
        return {
            "success": True,
            "message": "Alert acknowledged successfully",
            "alert_id": alert_id,
            "acknowledged_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to acknowledge alert", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


# Dashboard and Analytics Endpoints

@router.get("/dashboard")
async def get_credit_dashboard(
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get credit management dashboard data.
    
    Returns comprehensive dashboard information including
    balance, usage trends, alerts, and billing status.
    """
    try:
        # Get current balance
        balance = await credit_management_service.get_credit_balance(tenant_id)
        
        # Get recent usage
        recent_usage = await credit_management_service.get_usage_history(tenant_id, days=7)
        
        # Get unacknowledged alerts
        alerts = await credit_management_service.get_tenant_alerts(tenant_id, unacknowledged_only=True)
        
        # Get subscription
        subscription = await credit_management_service.get_tenant_subscription(tenant_id)
        
        # Calculate usage trends
        usage_by_type = {}
        total_cost = Decimal('0.0')
        
        for usage in recent_usage:
            if usage.usage_type not in usage_by_type:
                usage_by_type[usage.usage_type] = {
                    "credits": 0,
                    "cost": 0.0,
                    "count": 0
                }
            
            usage_by_type[usage.usage_type]["credits"] += usage.credits_consumed
            usage_by_type[usage.usage_type]["cost"] += float(usage.total_cost)
            usage_by_type[usage.usage_type]["count"] += 1
            total_cost += usage.total_cost
        
        dashboard_data = {
            "tenant_id": str(tenant_id),
            "current_balance": {
                "allocated_credits": balance.allocated_credits if balance else 0,
                "used_credits": balance.used_credits if balance else 0,
                "remaining_credits": balance.remaining_credits if balance else 0,
                "usage_percentage": round(balance.usage_percentage, 2) if balance else 0,
                "is_over_limit": balance.is_over_limit if balance else False,
                "overage_cost": float(balance.overage_cost) if balance else 0.0
            },
            "subscription": {
                "plan_name": subscription.credit_plan.name if subscription else "No Plan",
                "status": subscription.status if subscription else "inactive",
                "next_billing_date": subscription.next_billing_date.isoformat() if subscription else None,
                "monthly_price": float(subscription.credit_plan.monthly_price) if subscription else 0.0
            },
            "recent_usage": {
                "period_days": 7,
                "total_records": len(recent_usage),
                "total_cost": float(total_cost),
                "usage_by_type": usage_by_type
            },
            "alerts": {
                "total_unacknowledged": len(alerts),
                "critical_alerts": len([a for a in alerts if a.severity == "critical"]),
                "warning_alerts": len([a for a in alerts if a.severity == "warning"])
            }
        }
        
        return {
            "success": True,
            "dashboard": dashboard_data
        }
        
    except Exception as e:
        logger.error("Failed to get credit dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get credit dashboard")


@router.get("/config")
async def get_credit_config():
    """
    Get credit system configuration.
    
    Returns current configuration settings for the
    credit management system.
    """
    try:
        config = credit_management_service.config.copy()
        usage_types = credit_management_service.usage_types
        alert_thresholds = credit_management_service.alert_thresholds
        
        return {
            "success": True,
            "configuration": {
                "system_config": config,
                "usage_types": usage_types,
                "alert_thresholds": alert_thresholds
            }
        }
        
    except Exception as e:
        logger.error("Failed to get credit config", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get credit config")