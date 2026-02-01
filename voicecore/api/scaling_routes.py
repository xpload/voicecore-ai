"""
Auto-scaling API routes for VoiceCore AI.

Provides endpoints for auto-scaling management, performance monitoring,
and capacity management per Requirements 11.1 and 11.3.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from voicecore.services.auto_scaling_service import (
    AutoScalingService, ScalingPolicy, ScalingAction, ScalingStatus
)
from voicecore.services.performance_monitoring_service import (
    PerformanceMonitoringService, AlertSeverity
)
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/scaling", tags=["auto-scaling"])

# Initialize services
auto_scaling_service = AutoScalingService()
performance_service = PerformanceMonitoringService()


# Request/Response models
class ScalingPolicyRequest(BaseModel):
    """Request model for scaling policy configuration."""
    name: str = Field(..., description="Policy name")
    enabled: bool = Field(True, description="Whether policy is enabled")
    min_instances: int = Field(1, ge=1, le=100, description="Minimum instances")
    max_instances: int = Field(10, ge=1, le=100, description="Maximum instances")
    target_utilization: float = Field(0.65, ge=0.1, le=0.9, description="Target utilization")
    scale_up_threshold: float = Field(0.75, ge=0.1, le=1.0, description="Scale up threshold")
    scale_down_threshold: float = Field(0.30, ge=0.1, le=1.0, description="Scale down threshold")
    scale_up_cooldown: int = Field(300, ge=60, le=3600, description="Scale up cooldown (seconds)")
    scale_down_cooldown: int = Field(600, ge=60, le=3600, description="Scale down cooldown (seconds)")
    scale_up_increment: int = Field(1, ge=1, le=10, description="Scale up increment")
    scale_down_decrement: int = Field(1, ge=1, le=10, description="Scale down decrement")
    evaluation_period: int = Field(60, ge=30, le=600, description="Evaluation period (seconds)")


class ScalingPolicyResponse(BaseModel):
    """Response model for scaling policy."""
    name: str
    enabled: bool
    min_instances: int
    max_instances: int
    target_utilization: float
    scale_up_threshold: float
    scale_down_threshold: float
    scale_up_cooldown: int
    scale_down_cooldown: int
    scale_up_increment: int
    scale_down_decrement: int
    evaluation_period: int


class ScalingStatusResponse(BaseModel):
    """Response model for scaling status."""
    status: str
    current_instances: int
    last_scaling_event: Optional[Dict[str, Any]]
    policy: Dict[str, Any]
    total_scaling_events: int
    monitoring_active: bool


class ScalingRecommendationResponse(BaseModel):
    """Response model for scaling recommendation."""
    action: str
    target_instances: int
    current_instances: int
    reason: str
    confidence: float
    estimated_cost_impact: Optional[float] = None


class PerformanceMetricsResponse(BaseModel):
    """Response model for performance metrics."""
    timestamp: str
    system: Dict[str, Any]
    application: Dict[str, Any]
    database: Dict[str, Any]
    external_services: Dict[str, Any]


class SystemCapacityResponse(BaseModel):
    """Response model for system capacity."""
    max_concurrent_calls: int
    current_concurrent_calls: int
    available_capacity: int
    utilization_percentage: float
    estimated_time_to_capacity: Optional[int]


class PerformanceAlertResponse(BaseModel):
    """Response model for performance alert."""
    id: str
    severity: str
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    timestamp: str
    tenant_id: Optional[str]
    resolved: bool


# Dependency functions
async def get_tenant_id(tenant_id: Optional[str] = Query(None)) -> Optional[uuid.UUID]:
    """Extract tenant ID from query parameter."""
    if tenant_id:
        try:
            return uuid.UUID(tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid tenant ID format"
            )
    return None


# Auto-scaling management endpoints
@router.get("/status", response_model=ScalingStatusResponse)
async def get_scaling_status():
    """
    Get current auto-scaling status.
    
    Returns current scaling configuration, status, and recent activity.
    """
    try:
        status = auto_scaling_service.get_scaling_status()
        return ScalingStatusResponse(**status)
        
    except Exception as e:
        logger.error("Failed to get scaling status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve scaling status"
        )


@router.post("/start")
async def start_auto_scaling():
    """
    Start auto-scaling monitoring.
    
    Enables automatic scaling based on performance metrics.
    """
    try:
        await auto_scaling_service.start_auto_scaling()
        
        return {
            "message": "Auto-scaling started successfully",
            "status": "enabled"
        }
        
    except Exception as e:
        logger.error("Failed to start auto-scaling", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to start auto-scaling"
        )


@router.post("/stop")
async def stop_auto_scaling():
    """
    Stop auto-scaling monitoring.
    
    Disables automatic scaling while maintaining current instance count.
    """
    try:
        await auto_scaling_service.stop_auto_scaling()
        
        return {
            "message": "Auto-scaling stopped successfully",
            "status": "disabled"
        }
        
    except Exception as e:
        logger.error("Failed to stop auto-scaling", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to stop auto-scaling"
        )


@router.get("/recommendation", response_model=ScalingRecommendationResponse)
async def get_scaling_recommendation(
    tenant_id: Optional[uuid.UUID] = Depends(get_tenant_id)
):
    """
    Get current scaling recommendation.
    
    Evaluates current system state and returns scaling recommendation.
    """
    try:
        recommendation = await auto_scaling_service.evaluate_scaling_decision(tenant_id)
        
        return ScalingRecommendationResponse(
            action=recommendation.action,
            target_instances=recommendation.target_instances,
            current_instances=recommendation.current_instances,
            reason=recommendation.reason,
            confidence=recommendation.confidence,
            estimated_cost_impact=recommendation.estimated_cost_impact
        )
        
    except Exception as e:
        logger.error("Failed to get scaling recommendation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to generate scaling recommendation"
        )


@router.post("/evaluate")
async def force_scaling_evaluation(
    tenant_id: Optional[uuid.UUID] = Depends(get_tenant_id)
):
    """
    Force immediate scaling evaluation and action.
    
    Performs immediate evaluation and executes scaling action if needed.
    """
    try:
        result = await auto_scaling_service.force_scaling_evaluation(tenant_id)
        
        return {
            "message": "Scaling evaluation completed",
            "result": result
        }
        
    except Exception as e:
        logger.error("Failed to force scaling evaluation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to perform scaling evaluation"
        )


@router.get("/history")
async def get_scaling_history(
    hours: int = Query(24, ge=1, le=168, description="Hours of history"),
    tenant_id: Optional[uuid.UUID] = Depends(get_tenant_id)
):
    """
    Get scaling event history.
    
    Returns recent scaling events and their outcomes.
    """
    try:
        events = auto_scaling_service.get_scaling_history(hours, tenant_id)
        
        return {
            "period": {
                "hours": hours,
                "events_count": len(events)
            },
            "events": [
                {
                    "id": event.id,
                    "timestamp": event.timestamp.isoformat(),
                    "action": event.action.value,
                    "from_instances": event.from_instances,
                    "to_instances": event.to_instances,
                    "reason": event.reason,
                    "success": event.success,
                    "duration_seconds": event.duration_seconds,
                    "error_message": event.error_message
                }
                for event in events
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get scaling history", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve scaling history"
        )


# Scaling policy management endpoints
@router.get("/policy", response_model=ScalingPolicyResponse)
async def get_scaling_policy(
    tenant_id: Optional[uuid.UUID] = Depends(get_tenant_id)
):
    """
    Get current scaling policy.
    
    Returns scaling policy configuration for tenant or default.
    """
    try:
        policy = auto_scaling_service.get_scaling_policy(tenant_id)
        
        return ScalingPolicyResponse(
            name=policy.name,
            enabled=policy.enabled,
            min_instances=policy.min_instances,
            max_instances=policy.max_instances,
            target_utilization=policy.target_utilization,
            scale_up_threshold=policy.scale_up_threshold,
            scale_down_threshold=policy.scale_down_threshold,
            scale_up_cooldown=policy.scale_up_cooldown,
            scale_down_cooldown=policy.scale_down_cooldown,
            scale_up_increment=policy.scale_up_increment,
            scale_down_decrement=policy.scale_down_decrement,
            evaluation_period=policy.evaluation_period
        )
        
    except Exception as e:
        logger.error("Failed to get scaling policy", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve scaling policy"
        )


@router.put("/policy", response_model=ScalingPolicyResponse)
async def update_scaling_policy(
    policy_request: ScalingPolicyRequest,
    tenant_id: Optional[uuid.UUID] = Depends(get_tenant_id)
):
    """
    Update scaling policy.
    
    Updates scaling policy configuration for tenant or default.
    """
    try:
        # Validate policy configuration
        if policy_request.min_instances >= policy_request.max_instances:
            raise HTTPException(
                status_code=400,
                detail="Minimum instances must be less than maximum instances"
            )
        
        if policy_request.scale_down_threshold >= policy_request.scale_up_threshold:
            raise HTTPException(
                status_code=400,
                detail="Scale down threshold must be less than scale up threshold"
            )
        
        # Create scaling policy
        policy = ScalingPolicy(
            name=policy_request.name,
            enabled=policy_request.enabled,
            min_instances=policy_request.min_instances,
            max_instances=policy_request.max_instances,
            target_utilization=policy_request.target_utilization,
            scale_up_threshold=policy_request.scale_up_threshold,
            scale_down_threshold=policy_request.scale_down_threshold,
            scale_up_cooldown=policy_request.scale_up_cooldown,
            scale_down_cooldown=policy_request.scale_down_cooldown,
            scale_up_increment=policy_request.scale_up_increment,
            scale_down_decrement=policy_request.scale_down_decrement,
            evaluation_period=policy_request.evaluation_period
        )
        
        # Set policy
        auto_scaling_service.set_scaling_policy(policy, tenant_id)
        
        return ScalingPolicyResponse(
            name=policy.name,
            enabled=policy.enabled,
            min_instances=policy.min_instances,
            max_instances=policy.max_instances,
            target_utilization=policy.target_utilization,
            scale_up_threshold=policy.scale_up_threshold,
            scale_down_threshold=policy.scale_down_threshold,
            scale_up_cooldown=policy.scale_up_cooldown,
            scale_down_cooldown=policy.scale_down_cooldown,
            scale_up_increment=policy.scale_up_increment,
            scale_down_decrement=policy.scale_down_decrement,
            evaluation_period=policy.evaluation_period
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update scaling policy", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to update scaling policy"
        )


# Performance monitoring endpoints
@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    tenant_id: Optional[uuid.UUID] = Depends(get_tenant_id)
):
    """
    Get current performance metrics.
    
    Returns comprehensive system performance data.
    """
    try:
        metrics = await performance_service.collect_system_metrics(tenant_id)
        
        return PerformanceMetricsResponse(**metrics)
        
    except Exception as e:
        logger.error("Failed to get performance metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve performance metrics"
        )


@router.get("/capacity", response_model=SystemCapacityResponse)
async def get_system_capacity(
    tenant_id: Optional[uuid.UUID] = Depends(get_tenant_id)
):
    """
    Get current system capacity information.
    
    Returns capacity utilization and availability data.
    """
    try:
        capacity = await performance_service.get_system_capacity(tenant_id)
        
        return SystemCapacityResponse(
            max_concurrent_calls=capacity.max_concurrent_calls,
            current_concurrent_calls=capacity.current_concurrent_calls,
            available_capacity=capacity.available_capacity,
            utilization_percentage=capacity.utilization_percentage,
            estimated_time_to_capacity=capacity.estimated_time_to_capacity
        )
        
    except Exception as e:
        logger.error("Failed to get system capacity", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve system capacity"
        )


@router.get("/trends")
async def get_performance_trends(
    hours: int = Query(24, ge=1, le=168, description="Hours of trend data"),
    tenant_id: Optional[uuid.UUID] = Depends(get_tenant_id)
):
    """
    Get performance trends analysis.
    
    Returns trend analysis for key performance metrics.
    """
    try:
        trends = await performance_service.analyze_performance_trends(tenant_id, hours)
        
        return {
            "message": "Performance trends retrieved successfully",
            "trends": trends
        }
        
    except Exception as e:
        logger.error("Failed to get performance trends", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve performance trends"
        )


@router.get("/alerts", response_model=List[PerformanceAlertResponse])
async def get_performance_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    tenant_id: Optional[uuid.UUID] = Depends(get_tenant_id)
):
    """
    Get active performance alerts.
    
    Returns current performance alerts and warnings.
    """
    try:
        # Parse severity filter
        severity_filter = None
        if severity:
            try:
                severity_filter = AlertSeverity(severity.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid severity: {severity}"
                )
        
        alerts = await performance_service.get_active_alerts(tenant_id, severity_filter)
        
        return [
            PerformanceAlertResponse(
                id=alert.id,
                severity=alert.severity.value,
                metric_name=alert.metric_name,
                current_value=alert.current_value,
                threshold_value=alert.threshold_value,
                message=alert.message,
                timestamp=alert.timestamp.isoformat(),
                tenant_id=str(alert.tenant_id) if alert.tenant_id else None,
                resolved=alert.resolved
            )
            for alert in alerts
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get performance alerts", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve performance alerts"
        )


@router.post("/alerts/{alert_id}/resolve")
async def resolve_performance_alert(alert_id: str):
    """
    Resolve a performance alert.
    
    Marks the specified alert as resolved.
    """
    try:
        success = await performance_service.resolve_alert(alert_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Alert not found"
            )
        
        return {
            "message": "Alert resolved successfully",
            "alert_id": alert_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to resolve alert", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to resolve alert"
        )


# Health check endpoint
@router.get("/health")
async def scaling_health_check():
    """
    Health check endpoint for auto-scaling service.
    
    Returns service health and status information.
    """
    try:
        status = auto_scaling_service.get_scaling_status()
        
        return {
            "status": "healthy",
            "service": "auto-scaling",
            "timestamp": datetime.utcnow().isoformat(),
            "scaling_enabled": status["status"] == "enabled",
            "monitoring_active": status["monitoring_active"]
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "auto-scaling",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }