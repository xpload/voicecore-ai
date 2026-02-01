"""
API routes for error handling and system diagnostics.

Provides endpoints for error reporting, system health monitoring,
and debugging per Requirements 9.5 and 9.6.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from voicecore.services.error_handling_service import (
    error_handling_service, ErrorSeverity, ErrorCategory, SystemComponent
)
from voicecore.services.auth_service import get_current_tenant
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/system", tags=["System Diagnostics & Error Handling"])


# Request/Response Models

class ReportErrorRequest(BaseModel):
    """Request model for reporting system errors."""
    component: str = Field(..., description="System component")
    category: str = Field(..., description="Error category")
    severity: str = Field(..., description="Error severity")
    error_type: str = Field(..., description="Error type")
    error_message: str = Field(..., description="Error message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    
    def validate_enums(self):
        """Validate enum values."""
        try:
            SystemComponent(self.component)
            ErrorCategory(self.category)
            ErrorSeverity(self.severity)
        except ValueError as e:
            raise ValueError(f"Invalid enum value: {str(e)}")


class ResolveErrorRequest(BaseModel):
    """Request model for resolving errors."""
    resolution_notes: str = Field(..., description="Resolution notes")
    resolved_by: Optional[str] = Field(None, description="Who resolved the error")


class RecordHealthMetricRequest(BaseModel):
    """Request model for recording health metrics."""
    component: str = Field(..., description="System component")
    metric_name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    threshold: Optional[float] = Field(None, description="Custom threshold")
    
    def validate_component(self):
        """Validate component enum."""
        try:
            SystemComponent(self.component)
        except ValueError:
            raise ValueError(f"Invalid component: {self.component}")


# Error Reporting Endpoints

@router.post("/errors/report")
async def report_system_error(
    request: ReportErrorRequest,
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant)
):
    """
    Report a system error.
    
    Records a system error with comprehensive context for
    debugging and monitoring purposes.
    """
    try:
        # Validate enum values
        request.validate_enums()
        
        # Create a mock exception for reporting
        class ReportedException(Exception):
            pass
        
        mock_error = ReportedException(request.error_message)
        
        # Report the error
        error_report = await error_handling_service.report_error(
            component=SystemComponent(request.component),
            category=ErrorCategory(request.category),
            severity=ErrorSeverity(request.severity),
            error=mock_error,
            context=request.context,
            tenant_id=tenant_id,
            correlation_id=request.correlation_id
        )
        
        return {
            "success": True,
            "error_report": {
                "id": error_report.id,
                "component": error_report.component.value,
                "category": error_report.category.value,
                "severity": error_report.severity.value,
                "error_type": error_report.error_type,
                "error_message": error_report.error_message,
                "timestamp": error_report.timestamp.isoformat(),
                "correlation_id": error_report.correlation_id
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to report system error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to report system error")


@router.get("/errors")
async def get_error_reports(
    component: Optional[str] = Query(None, description="Filter by component"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant)
):
    """
    Get system error reports.
    
    Returns filtered error reports for system monitoring
    and debugging purposes.
    """
    try:
        # Validate enum parameters
        component_enum = None
        if component:
            try:
                component_enum = SystemComponent(component)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid component: {component}")
        
        severity_enum = None
        if severity:
            try:
                severity_enum = ErrorSeverity(severity)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        # Get error reports
        error_reports = await error_handling_service.get_error_reports(
            component=component_enum,
            severity=severity_enum,
            hours=hours,
            resolved=resolved
        )
        
        return {
            "success": True,
            "filters": {
                "component": component,
                "severity": severity,
                "hours": hours,
                "resolved": resolved
            },
            "total_reports": len(error_reports),
            "error_reports": [
                {
                    "id": report.id,
                    "tenant_id": str(report.tenant_id) if report.tenant_id else None,
                    "component": report.component.value,
                    "category": report.category.value,
                    "severity": report.severity.value,
                    "error_type": report.error_type,
                    "error_message": report.error_message,
                    "correlation_id": report.correlation_id,
                    "request_path": report.request_path,
                    "request_method": report.request_method,
                    "timestamp": report.timestamp.isoformat(),
                    "resolved": report.resolved,
                    "resolution_notes": report.resolution_notes,
                    "resolved_at": report.resolved_at.isoformat() if report.resolved_at else None
                }
                for report in error_reports
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get error reports", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get error reports")


@router.get("/errors/{error_id}")
async def get_error_report(
    error_id: str,
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant)
):
    """
    Get detailed error report.
    
    Returns comprehensive details about a specific error
    including stack trace and context information.
    """
    try:
        if error_id not in error_handling_service.error_reports:
            raise HTTPException(status_code=404, detail="Error report not found")
        
        error_report = error_handling_service.error_reports[error_id]
        
        # Check tenant access (if tenant_id is provided)
        if tenant_id and error_report.tenant_id and error_report.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "success": True,
            "error_report": {
                "id": error_report.id,
                "tenant_id": str(error_report.tenant_id) if error_report.tenant_id else None,
                "component": error_report.component.value,
                "category": error_report.category.value,
                "severity": error_report.severity.value,
                "error_type": error_report.error_type,
                "error_message": error_report.error_message,
                "stack_trace": error_report.stack_trace,
                "context": error_report.context,
                "correlation_id": error_report.correlation_id,
                "user_id": error_report.user_id,
                "request_path": error_report.request_path,
                "request_method": error_report.request_method,
                "timestamp": error_report.timestamp.isoformat(),
                "resolved": error_report.resolved,
                "resolution_notes": error_report.resolution_notes,
                "resolved_at": error_report.resolved_at.isoformat() if error_report.resolved_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get error report", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get error report")


@router.put("/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    request: ResolveErrorRequest,
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant)
):
    """
    Resolve an error report.
    
    Marks an error as resolved with resolution notes
    for tracking and analysis purposes.
    """
    try:
        success = await error_handling_service.resolve_error(
            error_id=error_id,
            resolution_notes=request.resolution_notes,
            resolved_by=request.resolved_by
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Error report not found")
        
        return {
            "success": True,
            "message": "Error resolved successfully",
            "error_id": error_id,
            "resolved_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to resolve error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to resolve error")


# System Health Monitoring Endpoints

@router.post("/health/metrics")
async def record_health_metric(
    request: RecordHealthMetricRequest,
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant)
):
    """
    Record a system health metric.
    
    Records system performance and health metrics
    for monitoring and alerting purposes.
    """
    try:
        # Validate component
        request.validate_component()
        
        # Record health metric
        health_metric = await error_handling_service.record_health_metric(
            component=SystemComponent(request.component),
            metric_name=request.metric_name,
            value=request.value,
            threshold=request.threshold
        )
        
        return {
            "success": True,
            "health_metric": {
                "component": health_metric.component.value,
                "metric_name": health_metric.metric_name,
                "value": health_metric.value,
                "threshold": health_metric.threshold,
                "status": health_metric.status,
                "timestamp": health_metric.timestamp.isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to record health metric", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to record health metric")


@router.get("/health")
async def get_system_health():
    """
    Get overall system health status.
    
    Returns comprehensive system health information
    including component status and critical issues.
    """
    try:
        health_status = await error_handling_service.get_system_health()
        
        return {
            "success": True,
            "system_health": health_status
        }
        
    except Exception as e:
        logger.error("Failed to get system health", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get system health")


@router.get("/health/{component}")
async def get_component_health(component: str):
    """
    Get health status for a specific component.
    
    Returns detailed health information for a
    specific system component.
    """
    try:
        # Validate component
        try:
            component_enum = SystemComponent(component)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid component: {component}")
        
        # Get overall health and filter for component
        health_status = await error_handling_service.get_system_health()
        
        component_health = health_status.get("components", {}).get(component)
        if not component_health:
            raise HTTPException(status_code=404, detail="Component health data not found")
        
        return {
            "success": True,
            "component": component,
            "health_status": component_health
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get component health", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get component health")


# Diagnostics and Debugging Endpoints

@router.get("/diagnostics")
async def generate_diagnostic_report(
    component: Optional[str] = Query(None, description="Filter by component"),
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant)
):
    """
    Generate comprehensive diagnostic report.
    
    Creates a detailed diagnostic report including error
    statistics, health metrics, and recovery actions.
    """
    try:
        # Validate component if provided
        component_enum = None
        if component:
            try:
                component_enum = SystemComponent(component)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid component: {component}")
        
        # Generate diagnostic report
        diagnostic_report = await error_handling_service.generate_diagnostic_report(
            component=component_enum,
            hours=hours
        )
        
        return {
            "success": True,
            "diagnostic_report": diagnostic_report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate diagnostic report", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate diagnostic report")


@router.get("/recovery/actions")
async def get_recovery_actions():
    """
    Get registered recovery actions.
    
    Returns all registered automated recovery actions
    and their configuration.
    """
    try:
        recovery_actions = error_handling_service.recovery_actions
        
        return {
            "success": True,
            "total_actions": len(recovery_actions),
            "recovery_actions": [
                {
                    "id": action.id,
                    "error_pattern": action.error_pattern,
                    "component": action.component.value,
                    "action_type": action.action_type,
                    "action_function": action.action_function,
                    "max_attempts": action.max_attempts,
                    "cooldown_seconds": action.cooldown_seconds,
                    "enabled": action.enabled
                }
                for action in recovery_actions.values()
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get recovery actions", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get recovery actions")


@router.get("/recovery/attempts")
async def get_recovery_attempts():
    """
    Get recent recovery attempt statistics.
    
    Returns information about recent automated
    recovery attempts and their success rates.
    """
    try:
        recovery_attempts = error_handling_service.recovery_attempts
        
        return {
            "success": True,
            "total_attempts": len(recovery_attempts),
            "recovery_attempts": [
                {
                    "action_key": key,
                    "attempts": data["attempts"],
                    "last_attempt": data["last_attempt"].isoformat()
                }
                for key, data in recovery_attempts.items()
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get recovery attempts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get recovery attempts")


# Configuration Endpoints

@router.get("/config/error-thresholds")
async def get_error_thresholds():
    """
    Get error threshold configuration.
    
    Returns current error rate thresholds for
    different severity levels.
    """
    try:
        thresholds = {
            severity.value: threshold
            for severity, threshold in error_handling_service.error_thresholds.items()
        }
        
        return {
            "success": True,
            "error_thresholds": thresholds
        }
        
    except Exception as e:
        logger.error("Failed to get error thresholds", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get error thresholds")


@router.get("/config/health-thresholds")
async def get_health_thresholds():
    """
    Get health metric threshold configuration.
    
    Returns current health metric thresholds for
    system monitoring.
    """
    try:
        return {
            "success": True,
            "health_thresholds": error_handling_service.health_thresholds
        }
        
    except Exception as e:
        logger.error("Failed to get health thresholds", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get health thresholds")


# Utility Endpoints

@router.get("/components")
async def list_system_components():
    """
    List available system components.
    
    Returns all system components that can be
    monitored and managed.
    """
    try:
        components = [
            {
                "value": component.value,
                "name": component.value.replace("_", " ").title(),
                "description": f"{component.value.replace('_', ' ').title()} component"
            }
            for component in SystemComponent
        ]
        
        return {
            "success": True,
            "system_components": components
        }
        
    except Exception as e:
        logger.error("Failed to list system components", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list system components")


@router.get("/categories")
async def list_error_categories():
    """
    List available error categories.
    
    Returns all error categories for classification
    and filtering purposes.
    """
    try:
        categories = [
            {
                "value": category.value,
                "name": category.value.replace("_", " ").title(),
                "description": f"{category.value.replace('_', ' ').title()} errors"
            }
            for category in ErrorCategory
        ]
        
        return {
            "success": True,
            "error_categories": categories
        }
        
    except Exception as e:
        logger.error("Failed to list error categories", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list error categories")


@router.get("/severities")
async def list_error_severities():
    """
    List available error severity levels.
    
    Returns all error severity levels for
    classification and prioritization.
    """
    try:
        severities = [
            {
                "value": severity.value,
                "name": severity.value.title(),
                "description": f"{severity.value.title()} severity errors"
            }
            for severity in ErrorSeverity
        ]
        
        return {
            "success": True,
            "error_severities": severities
        }
        
    except Exception as e:
        logger.error("Failed to list error severities", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list error severities")