"""
Comprehensive Error Handling Service for VoiceCore AI.

Implements system failure detection, reporting, and debugging logs
per Requirements 9.5 and 9.6.
"""

import uuid
import asyncio
import traceback
import sys
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    NETWORK = "network"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"
    CONFIGURATION = "configuration"


class SystemComponent(Enum):
    """System components for error tracking."""
    API_GATEWAY = "api_gateway"
    DATABASE = "database"
    TWILIO_SERVICE = "twilio_service"
    OPENAI_SERVICE = "openai_service"
    WEBSOCKET_SERVICE = "websocket_service"
    CREDIT_SYSTEM = "credit_system"
    ANALYTICS = "analytics"
    SECURITY = "security"
    MIDDLEWARE = "middleware"
    SCHEDULER = "scheduler"


@dataclass
class ErrorReport:
    """Comprehensive error report."""
    id: str
    tenant_id: Optional[uuid.UUID]
    component: SystemComponent
    category: ErrorCategory
    severity: ErrorSeverity
    error_type: str
    error_message: str
    stack_trace: Optional[str]
    context: Dict[str, Any]
    correlation_id: Optional[str]
    user_id: Optional[str]
    request_path: Optional[str]
    request_method: Optional[str]
    timestamp: datetime
    resolved: bool = False
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None


@dataclass
class SystemHealthMetric:
    """System health metric."""
    component: SystemComponent
    metric_name: str
    value: float
    threshold: float
    status: str  # "healthy", "warning", "critical"
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


@dataclass
class RecoveryAction:
    """Automated recovery action."""
    id: str
    error_pattern: str
    component: SystemComponent
    action_type: str  # "restart", "retry", "fallback", "alert"
    action_function: str
    max_attempts: int
    cooldown_seconds: int
    enabled: bool = True


class ErrorHandlingService:
    """
    Comprehensive error handling and system monitoring service.
    
    Implements system failure detection, reporting, and debugging
    per Requirements 9.5 and 9.6.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Error storage
        self.error_reports: Dict[str, ErrorReport] = {}
        self.health_metrics: Dict[str, List[SystemHealthMetric]] = {}
        
        # Recovery actions registry
        self.recovery_actions: Dict[str, RecoveryAction] = {}
        
        # Error patterns and thresholds
        self.error_thresholds = {
            ErrorSeverity.LOW: 100,      # 100 errors per hour
            ErrorSeverity.MEDIUM: 50,    # 50 errors per hour
            ErrorSeverity.HIGH: 10,      # 10 errors per hour
            ErrorSeverity.CRITICAL: 1    # 1 error per hour
        }
        
        # Health check thresholds
        self.health_thresholds = {
            "response_time_ms": 2000,
            "error_rate_percent": 5.0,
            "cpu_usage_percent": 80.0,
            "memory_usage_percent": 85.0,
            "database_connections": 90.0
        }
        
        # Recovery attempt tracking
        self.recovery_attempts: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default recovery actions
        self._initialize_recovery_actions()
    
    # Error Reporting and Detection
    
    async def report_error(
        self,
        component: SystemComponent,
        category: ErrorCategory,
        severity: ErrorSeverity,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_path: Optional[str] = None,
        request_method: Optional[str] = None
    ) -> ErrorReport:
        """Report a system error with comprehensive context."""
        try:
            error_id = str(uuid.uuid4())
            
            # Extract error information
            error_type = type(error).__name__
            error_message = str(error)
            stack_trace = traceback.format_exception(type(error), error, error.__traceback__)
            
            # Create error report
            error_report = ErrorReport(
                id=error_id,
                tenant_id=tenant_id,
                component=component,
                category=category,
                severity=severity,
                error_type=error_type,
                error_message=error_message,
                stack_trace=''.join(stack_trace),
                context=context or {},
                correlation_id=correlation_id,
                user_id=user_id,
                request_path=request_path,
                request_method=request_method,
                timestamp=datetime.utcnow()
            )
            
            # Store error report
            self.error_reports[error_id] = error_report
            
            # Log error with appropriate level
            log_data = {
                "error_id": error_id,
                "component": component.value,
                "category": category.value,
                "severity": severity.value,
                "error_type": error_type,
                "error_message": error_message,
                "correlation_id": correlation_id,
                "tenant_id": str(tenant_id) if tenant_id else None
            }
            
            if severity == ErrorSeverity.CRITICAL:
                self.logger.critical("Critical system error", **log_data)
            elif severity == ErrorSeverity.HIGH:
                self.logger.error("High severity error", **log_data)
            elif severity == ErrorSeverity.MEDIUM:
                self.logger.warning("Medium severity error", **log_data)
            else:
                self.logger.info("Low severity error", **log_data)
            
            # Check for error patterns and trigger recovery
            await self._check_error_patterns(error_report)
            
            # Check error rate thresholds
            await self._check_error_thresholds(component, severity)
            
            return error_report
            
        except Exception as e:
            # Fallback logging if error reporting fails
            self.logger.critical(
                "Error reporting system failure",
                original_error=str(error),
                reporting_error=str(e)
            )
            raise
    
    async def get_error_reports(
        self,
        component: Optional[SystemComponent] = None,
        severity: Optional[ErrorSeverity] = None,
        hours: int = 24,
        resolved: Optional[bool] = None
    ) -> List[ErrorReport]:
        """Get error reports with filtering."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            filtered_reports = []
            for report in self.error_reports.values():
                # Time filter
                if report.timestamp < cutoff_time:
                    continue
                
                # Component filter
                if component and report.component != component:
                    continue
                
                # Severity filter
                if severity and report.severity != severity:
                    continue
                
                # Resolution filter
                if resolved is not None and report.resolved != resolved:
                    continue
                
                filtered_reports.append(report)
            
            # Sort by timestamp (newest first)
            filtered_reports.sort(key=lambda x: x.timestamp, reverse=True)
            
            return filtered_reports
            
        except Exception as e:
            self.logger.error("Failed to get error reports", error=str(e))
            return []
    
    async def resolve_error(
        self,
        error_id: str,
        resolution_notes: str,
        resolved_by: Optional[str] = None
    ) -> bool:
        """Mark an error as resolved."""
        try:
            if error_id not in self.error_reports:
                return False
            
            error_report = self.error_reports[error_id]
            error_report.resolved = True
            error_report.resolution_notes = resolution_notes
            error_report.resolved_at = datetime.utcnow()
            
            self.logger.info(
                "Error resolved",
                error_id=error_id,
                resolved_by=resolved_by,
                resolution_notes=resolution_notes
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to resolve error", error=str(e))
            return False
    
    # System Health Monitoring
    
    async def record_health_metric(
        self,
        component: SystemComponent,
        metric_name: str,
        value: float,
        threshold: Optional[float] = None
    ) -> SystemHealthMetric:
        """Record a system health metric."""
        try:
            # Use default threshold if not provided
            if threshold is None:
                threshold = self.health_thresholds.get(metric_name, 100.0)
            
            # Determine status
            if value <= threshold * 0.7:
                status = "healthy"
            elif value <= threshold:
                status = "warning"
            else:
                status = "critical"
            
            # Create health metric
            health_metric = SystemHealthMetric(
                component=component,
                metric_name=metric_name,
                value=value,
                threshold=threshold,
                status=status,
                timestamp=datetime.utcnow()
            )
            
            # Store metric
            component_key = component.value
            if component_key not in self.health_metrics:
                self.health_metrics[component_key] = []
            
            self.health_metrics[component_key].append(health_metric)
            
            # Keep only recent metrics (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            self.health_metrics[component_key] = [
                m for m in self.health_metrics[component_key]
                if m.timestamp > cutoff_time
            ]
            
            # Log critical health issues
            if status == "critical":
                self.logger.warning(
                    "Critical health metric detected",
                    component=component.value,
                    metric=metric_name,
                    value=value,
                    threshold=threshold
                )
            
            return health_metric
            
        except Exception as e:
            self.logger.error("Failed to record health metric", error=str(e))
            raise
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        try:
            health_status = {
                "overall_status": "healthy",
                "components": {},
                "critical_issues": [],
                "warnings": [],
                "last_updated": datetime.utcnow().isoformat()
            }
            
            critical_count = 0
            warning_count = 0
            
            for component_key, metrics in self.health_metrics.items():
                if not metrics:
                    continue
                
                # Get latest metrics for each metric type
                latest_metrics = {}
                for metric in metrics:
                    if (metric.metric_name not in latest_metrics or 
                        metric.timestamp > latest_metrics[metric.metric_name].timestamp):
                        latest_metrics[metric.metric_name] = metric
                
                # Analyze component health
                component_status = "healthy"
                component_issues = []
                
                for metric in latest_metrics.values():
                    if metric.status == "critical":
                        critical_count += 1
                        component_status = "critical"
                        component_issues.append({
                            "metric": metric.metric_name,
                            "value": metric.value,
                            "threshold": metric.threshold,
                            "status": metric.status
                        })
                    elif metric.status == "warning" and component_status != "critical":
                        warning_count += 1
                        component_status = "warning"
                        component_issues.append({
                            "metric": metric.metric_name,
                            "value": metric.value,
                            "threshold": metric.threshold,
                            "status": metric.status
                        })
                
                health_status["components"][component_key] = {
                    "status": component_status,
                    "metrics": {
                        metric.metric_name: {
                            "value": metric.value,
                            "threshold": metric.threshold,
                            "status": metric.status,
                            "timestamp": metric.timestamp.isoformat()
                        }
                        for metric in latest_metrics.values()
                    },
                    "issues": component_issues
                }
            
            # Determine overall status
            if critical_count > 0:
                health_status["overall_status"] = "critical"
            elif warning_count > 0:
                health_status["overall_status"] = "warning"
            
            # Get recent errors
            recent_errors = await self.get_error_reports(hours=1, resolved=False)
            critical_errors = [e for e in recent_errors if e.severity == ErrorSeverity.CRITICAL]
            
            if critical_errors:
                health_status["overall_status"] = "critical"
                health_status["critical_issues"].extend([
                    {
                        "type": "error",
                        "component": error.component.value,
                        "message": error.error_message,
                        "timestamp": error.timestamp.isoformat()
                    }
                    for error in critical_errors[:5]  # Latest 5 critical errors
                ])
            
            return health_status
            
        except Exception as e:
            self.logger.error("Failed to get system health", error=str(e))
            return {
                "overall_status": "unknown",
                "error": "Failed to retrieve system health",
                "last_updated": datetime.utcnow().isoformat()
            }
    
    # Automated Recovery
    
    def register_recovery_action(
        self,
        error_pattern: str,
        component: SystemComponent,
        action_type: str,
        action_function: str,
        max_attempts: int = 3,
        cooldown_seconds: int = 60
    ) -> str:
        """Register an automated recovery action."""
        try:
            action_id = str(uuid.uuid4())
            
            recovery_action = RecoveryAction(
                id=action_id,
                error_pattern=error_pattern,
                component=component,
                action_type=action_type,
                action_function=action_function,
                max_attempts=max_attempts,
                cooldown_seconds=cooldown_seconds
            )
            
            self.recovery_actions[action_id] = recovery_action
            
            self.logger.info(
                "Recovery action registered",
                action_id=action_id,
                pattern=error_pattern,
                component=component.value,
                action_type=action_type
            )
            
            return action_id
            
        except Exception as e:
            self.logger.error("Failed to register recovery action", error=str(e))
            raise
    
    async def _check_error_patterns(self, error_report: ErrorReport):
        """Check if error matches any recovery patterns."""
        try:
            for action in self.recovery_actions.values():
                if not action.enabled:
                    continue
                
                if action.component != error_report.component:
                    continue
                
                # Simple pattern matching (could be enhanced with regex)
                if action.error_pattern.lower() in error_report.error_message.lower():
                    await self._execute_recovery_action(action, error_report)
                    
        except Exception as e:
            self.logger.error("Failed to check error patterns", error=str(e))
    
    async def _execute_recovery_action(
        self,
        action: RecoveryAction,
        error_report: ErrorReport
    ):
        """Execute a recovery action."""
        try:
            action_key = f"{action.id}_{error_report.component.value}"
            
            # Check cooldown and attempt limits
            if action_key in self.recovery_attempts:
                attempt_data = self.recovery_attempts[action_key]
                
                # Check cooldown
                if (datetime.utcnow() - attempt_data["last_attempt"]).total_seconds() < action.cooldown_seconds:
                    return
                
                # Check max attempts
                if attempt_data["attempts"] >= action.max_attempts:
                    self.logger.warning(
                        "Recovery action max attempts reached",
                        action_id=action.id,
                        component=error_report.component.value,
                        attempts=attempt_data["attempts"]
                    )
                    return
                
                attempt_data["attempts"] += 1
                attempt_data["last_attempt"] = datetime.utcnow()
            else:
                self.recovery_attempts[action_key] = {
                    "attempts": 1,
                    "last_attempt": datetime.utcnow()
                }
            
            self.logger.info(
                "Executing recovery action",
                action_id=action.id,
                action_type=action.action_type,
                component=error_report.component.value,
                error_id=error_report.id
            )
            
            # Execute recovery action based on type
            if action.action_type == "restart":
                await self._restart_component(error_report.component)
            elif action.action_type == "retry":
                await self._retry_operation(error_report)
            elif action.action_type == "fallback":
                await self._activate_fallback(error_report.component)
            elif action.action_type == "alert":
                await self._send_alert(error_report)
            
        except Exception as e:
            self.logger.error("Failed to execute recovery action", error=str(e))
    
    async def _check_error_thresholds(
        self,
        component: SystemComponent,
        severity: ErrorSeverity
    ):
        """Check if error rate exceeds thresholds."""
        try:
            # Count recent errors for this component and severity
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            error_count = len([
                error for error in self.error_reports.values()
                if (error.component == component and 
                    error.severity == severity and
                    error.timestamp > cutoff_time)
            ])
            
            threshold = self.error_thresholds.get(severity, 100)
            
            if error_count >= threshold:
                self.logger.critical(
                    "Error threshold exceeded",
                    component=component.value,
                    severity=severity.value,
                    error_count=error_count,
                    threshold=threshold
                )
                
                # Trigger high-level recovery actions
                await self._handle_threshold_breach(component, severity, error_count)
                
        except Exception as e:
            self.logger.error("Failed to check error thresholds", error=str(e))
    
    # Recovery Action Implementations
    
    async def _restart_component(self, component: SystemComponent):
        """Restart a system component."""
        self.logger.info("Restarting component", component=component.value)
        # Implementation would depend on component type
        # This is a placeholder for actual restart logic
    
    async def _retry_operation(self, error_report: ErrorReport):
        """Retry a failed operation."""
        self.logger.info("Retrying operation", error_id=error_report.id)
        # Implementation would depend on the specific operation
        # This is a placeholder for actual retry logic
    
    async def _activate_fallback(self, component: SystemComponent):
        """Activate fallback for a component."""
        self.logger.info("Activating fallback", component=component.value)
        # Implementation would depend on component type
        # This is a placeholder for actual fallback logic
    
    async def _send_alert(self, error_report: ErrorReport):
        """Send alert for critical error."""
        self.logger.critical(
            "Critical error alert",
            error_id=error_report.id,
            component=error_report.component.value,
            message=error_report.error_message
        )
        # Implementation would send alerts via email, SMS, etc.
    
    async def _handle_threshold_breach(
        self,
        component: SystemComponent,
        severity: ErrorSeverity,
        error_count: int
    ):
        """Handle error threshold breach."""
        self.logger.critical(
            "Handling threshold breach",
            component=component.value,
            severity=severity.value,
            error_count=error_count
        )
        # Implementation would trigger emergency procedures
    
    def _initialize_recovery_actions(self):
        """Initialize default recovery actions."""
        try:
            # Database connection recovery
            self.register_recovery_action(
                error_pattern="connection",
                component=SystemComponent.DATABASE,
                action_type="restart",
                action_function="restart_database_pool",
                max_attempts=3,
                cooldown_seconds=30
            )
            
            # External API retry
            self.register_recovery_action(
                error_pattern="timeout",
                component=SystemComponent.TWILIO_SERVICE,
                action_type="retry",
                action_function="retry_twilio_request",
                max_attempts=3,
                cooldown_seconds=10
            )
            
            # OpenAI service fallback
            self.register_recovery_action(
                error_pattern="rate limit",
                component=SystemComponent.OPENAI_SERVICE,
                action_type="fallback",
                action_function="activate_openai_fallback",
                max_attempts=1,
                cooldown_seconds=60
            )
            
        except Exception as e:
            self.logger.error("Failed to initialize recovery actions", error=str(e))
    
    # Debugging and Diagnostics
    
    async def generate_diagnostic_report(
        self,
        component: Optional[SystemComponent] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Generate comprehensive diagnostic report."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get error statistics
            errors = await self.get_error_reports(component=component, hours=hours)
            error_stats = {
                "total_errors": len(errors),
                "by_severity": {},
                "by_category": {},
                "resolved_count": len([e for e in errors if e.resolved]),
                "unresolved_count": len([e for e in errors if not e.resolved])
            }
            
            # Count by severity
            for severity in ErrorSeverity:
                count = len([e for e in errors if e.severity == severity])
                error_stats["by_severity"][severity.value] = count
            
            # Count by category
            for category in ErrorCategory:
                count = len([e for e in errors if e.category == category])
                error_stats["by_category"][category.value] = count
            
            # Get health metrics
            health_status = await self.get_system_health()
            
            # Get recovery action statistics
            recovery_stats = {
                "total_actions": len(self.recovery_actions),
                "enabled_actions": len([a for a in self.recovery_actions.values() if a.enabled]),
                "recent_executions": len([
                    attempt for attempt in self.recovery_attempts.values()
                    if (datetime.utcnow() - attempt["last_attempt"]).total_seconds() < hours * 3600
                ])
            }
            
            diagnostic_report = {
                "report_id": str(uuid.uuid4()),
                "generated_at": datetime.utcnow().isoformat(),
                "time_period_hours": hours,
                "component_filter": component.value if component else "all",
                "error_statistics": error_stats,
                "system_health": health_status,
                "recovery_statistics": recovery_stats,
                "recent_critical_errors": [
                    {
                        "id": error.id,
                        "component": error.component.value,
                        "category": error.category.value,
                        "message": error.error_message,
                        "timestamp": error.timestamp.isoformat(),
                        "resolved": error.resolved
                    }
                    for error in errors
                    if error.severity == ErrorSeverity.CRITICAL
                ][:10]  # Latest 10 critical errors
            }
            
            return diagnostic_report
            
        except Exception as e:
            self.logger.error("Failed to generate diagnostic report", error=str(e))
            return {
                "error": "Failed to generate diagnostic report",
                "generated_at": datetime.utcnow().isoformat()
            }


# Global service instance
error_handling_service = ErrorHandlingService()