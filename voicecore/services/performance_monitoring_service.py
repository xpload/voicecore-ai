"""
Performance monitoring service for VoiceCore AI.

Implements comprehensive performance monitoring, alerting,
and capacity management per Requirements 11.1 and 11.3.
"""

import uuid
import asyncio
import psutil
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import SystemMetrics, MetricType, Call, Agent
from voicecore.services.analytics_service import AnalyticsService
from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricThreshold(Enum):
    """Performance metric thresholds."""
    CPU_WARNING = 70.0
    CPU_CRITICAL = 85.0
    MEMORY_WARNING = 75.0
    MEMORY_CRITICAL = 90.0
    RESPONSE_TIME_WARNING = 1000.0  # ms
    RESPONSE_TIME_CRITICAL = 2000.0  # ms
    ERROR_RATE_WARNING = 0.05  # 5%
    ERROR_RATE_CRITICAL = 0.10  # 10%
    CONCURRENT_CALLS_WARNING = 800
    CONCURRENT_CALLS_CRITICAL = 950


@dataclass
class PerformanceAlert:
    """Performance alert data structure."""
    id: str
    severity: AlertSeverity
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime
    tenant_id: Optional[uuid.UUID] = None
    resolved: bool = False


@dataclass
class SystemCapacity:
    """System capacity information."""
    max_concurrent_calls: int
    current_concurrent_calls: int
    available_capacity: int
    utilization_percentage: float
    estimated_time_to_capacity: Optional[int]  # minutes


@dataclass
class ScalingRecommendation:
    """Auto-scaling recommendation."""
    action: str  # "scale_up", "scale_down", "maintain"
    target_instances: int
    current_instances: int
    reason: str
    confidence: float
    estimated_cost_impact: Optional[float] = None


class PerformanceMonitoringService:
    """
    Comprehensive performance monitoring and alerting service.
    
    Monitors system performance, generates alerts, and provides
    capacity management recommendations per Requirements 11.1 and 11.3.
    """
    
    def __init__(self):
        self.logger = logger
        self.analytics_service = AnalyticsService()
        
        # Alert storage (in production, use Redis or database)
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        
        # Performance history for trend analysis
        self.performance_history: List[Dict[str, Any]] = []
        
        # Scaling configuration
        self.scaling_config = {
            "min_instances": 1,
            "max_instances": 10,
            "scale_up_threshold": 0.75,  # 75% utilization
            "scale_down_threshold": 0.30,  # 30% utilization
            "scale_up_cooldown": 300,  # 5 minutes
            "scale_down_cooldown": 600,  # 10 minutes
            "target_utilization": 0.65  # 65% target
        }
        
        # Last scaling action timestamp
        self.last_scaling_action = None
    
    async def collect_system_metrics(
        self,
        tenant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Collect comprehensive system performance metrics.
        
        Args:
            tenant_id: Optional tenant ID for tenant-specific metrics
            
        Returns:
            Dict containing system metrics
        """
        try:
            current_time = datetime.utcnow()
            
            # System resource metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network metrics (simplified)
            network = psutil.net_io_counters()
            
            # Application-specific metrics
            app_metrics = await self._collect_application_metrics(tenant_id)
            
            # Database metrics
            db_metrics = await self._collect_database_metrics(tenant_id)
            
            # External service metrics
            external_metrics = await self._collect_external_service_metrics()
            
            metrics = {
                "timestamp": current_time.isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024**3),
                    "network_bytes_sent": network.bytes_sent,
                    "network_bytes_recv": network.bytes_recv
                },
                "application": app_metrics,
                "database": db_metrics,
                "external_services": external_metrics
            }
            
            # Store metrics for trend analysis
            self.performance_history.append(metrics)
            
            # Keep only last 1000 entries
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
            
            # Store in database if tenant_id provided
            if tenant_id:
                await self._store_metrics_in_database(tenant_id, metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error("Failed to collect system metrics", error=str(e))
            return {}
    
    async def analyze_performance_trends(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze performance trends over specified time period.
        
        Args:
            tenant_id: Optional tenant ID
            hours: Hours of history to analyze
            
        Returns:
            Dict containing trend analysis
        """
        try:
            # Get recent metrics
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            recent_metrics = [
                m for m in self.performance_history
                if datetime.fromisoformat(m["timestamp"]) > cutoff_time
            ]
            
            if not recent_metrics:
                return {"error": "No recent metrics available"}
            
            # Calculate trends
            trends = {
                "period": {
                    "start": cutoff_time.isoformat(),
                    "end": datetime.utcnow().isoformat(),
                    "hours": hours,
                    "data_points": len(recent_metrics)
                },
                "cpu": self._calculate_metric_trend(recent_metrics, "system.cpu_percent"),
                "memory": self._calculate_metric_trend(recent_metrics, "system.memory_percent"),
                "concurrent_calls": self._calculate_metric_trend(recent_metrics, "application.concurrent_calls"),
                "response_time": self._calculate_metric_trend(recent_metrics, "application.avg_response_time_ms"),
                "error_rate": self._calculate_metric_trend(recent_metrics, "application.error_rate"),
                "database_performance": self._calculate_metric_trend(recent_metrics, "database.avg_query_time_ms")
            }
            
            # Add capacity analysis
            trends["capacity"] = await self._analyze_capacity_trends(recent_metrics)
            
            # Add scaling recommendations
            trends["scaling_recommendation"] = await self._generate_scaling_recommendation(trends)
            
            return trends
            
        except Exception as e:
            self.logger.error("Failed to analyze performance trends", error=str(e))
            return {"error": "Failed to analyze trends"}
    
    async def check_performance_thresholds(
        self,
        metrics: Dict[str, Any],
        tenant_id: Optional[uuid.UUID] = None
    ) -> List[PerformanceAlert]:
        """
        Check metrics against performance thresholds and generate alerts.
        
        Args:
            metrics: System metrics to check
            tenant_id: Optional tenant ID
            
        Returns:
            List of performance alerts
        """
        alerts = []
        
        try:
            # CPU threshold checks
            cpu_percent = metrics.get("system", {}).get("cpu_percent", 0)
            if cpu_percent >= MetricThreshold.CPU_CRITICAL.value:
                alerts.append(self._create_alert(
                    "cpu_critical", AlertSeverity.CRITICAL,
                    "CPU Usage", cpu_percent, MetricThreshold.CPU_CRITICAL.value,
                    f"Critical CPU usage: {cpu_percent:.1f}%", tenant_id
                ))
            elif cpu_percent >= MetricThreshold.CPU_WARNING.value:
                alerts.append(self._create_alert(
                    "cpu_warning", AlertSeverity.HIGH,
                    "CPU Usage", cpu_percent, MetricThreshold.CPU_WARNING.value,
                    f"High CPU usage: {cpu_percent:.1f}%", tenant_id
                ))
            
            # Memory threshold checks
            memory_percent = metrics.get("system", {}).get("memory_percent", 0)
            if memory_percent >= MetricThreshold.MEMORY_CRITICAL.value:
                alerts.append(self._create_alert(
                    "memory_critical", AlertSeverity.CRITICAL,
                    "Memory Usage", memory_percent, MetricThreshold.MEMORY_CRITICAL.value,
                    f"Critical memory usage: {memory_percent:.1f}%", tenant_id
                ))
            elif memory_percent >= MetricThreshold.MEMORY_WARNING.value:
                alerts.append(self._create_alert(
                    "memory_warning", AlertSeverity.HIGH,
                    "Memory Usage", memory_percent, MetricThreshold.MEMORY_WARNING.value,
                    f"High memory usage: {memory_percent:.1f}%", tenant_id
                ))
            
            # Response time threshold checks
            response_time = metrics.get("application", {}).get("avg_response_time_ms", 0)
            if response_time >= MetricThreshold.RESPONSE_TIME_CRITICAL.value:
                alerts.append(self._create_alert(
                    "response_time_critical", AlertSeverity.CRITICAL,
                    "Response Time", response_time, MetricThreshold.RESPONSE_TIME_CRITICAL.value,
                    f"Critical response time: {response_time:.1f}ms", tenant_id
                ))
            elif response_time >= MetricThreshold.RESPONSE_TIME_WARNING.value:
                alerts.append(self._create_alert(
                    "response_time_warning", AlertSeverity.HIGH,
                    "Response Time", response_time, MetricThreshold.RESPONSE_TIME_WARNING.value,
                    f"High response time: {response_time:.1f}ms", tenant_id
                ))
            
            # Error rate threshold checks
            error_rate = metrics.get("application", {}).get("error_rate", 0)
            if error_rate >= MetricThreshold.ERROR_RATE_CRITICAL.value:
                alerts.append(self._create_alert(
                    "error_rate_critical", AlertSeverity.CRITICAL,
                    "Error Rate", error_rate * 100, MetricThreshold.ERROR_RATE_CRITICAL.value * 100,
                    f"Critical error rate: {error_rate * 100:.1f}%", tenant_id
                ))
            elif error_rate >= MetricThreshold.ERROR_RATE_WARNING.value:
                alerts.append(self._create_alert(
                    "error_rate_warning", AlertSeverity.HIGH,
                    "Error Rate", error_rate * 100, MetricThreshold.ERROR_RATE_WARNING.value * 100,
                    f"High error rate: {error_rate * 100:.1f}%", tenant_id
                ))
            
            # Concurrent calls threshold checks
            concurrent_calls = metrics.get("application", {}).get("concurrent_calls", 0)
            if concurrent_calls >= MetricThreshold.CONCURRENT_CALLS_CRITICAL.value:
                alerts.append(self._create_alert(
                    "concurrent_calls_critical", AlertSeverity.CRITICAL,
                    "Concurrent Calls", concurrent_calls, MetricThreshold.CONCURRENT_CALLS_CRITICAL.value,
                    f"Critical concurrent calls: {concurrent_calls}", tenant_id
                ))
            elif concurrent_calls >= MetricThreshold.CONCURRENT_CALLS_WARNING.value:
                alerts.append(self._create_alert(
                    "concurrent_calls_warning", AlertSeverity.HIGH,
                    "Concurrent Calls", concurrent_calls, MetricThreshold.CONCURRENT_CALLS_WARNING.value,
                    f"High concurrent calls: {concurrent_calls}", tenant_id
                ))
            
            # Store active alerts
            for alert in alerts:
                self.active_alerts[alert.id] = alert
            
            return alerts
            
        except Exception as e:
            self.logger.error("Failed to check performance thresholds", error=str(e))
            return []
    
    async def get_system_capacity(
        self,
        tenant_id: Optional[uuid.UUID] = None
    ) -> SystemCapacity:
        """
        Get current system capacity information.
        
        Args:
            tenant_id: Optional tenant ID
            
        Returns:
            SystemCapacity object
        """
        try:
            # Get current metrics
            metrics = await self.collect_system_metrics(tenant_id)
            
            # Calculate capacity based on current performance
            current_calls = metrics.get("application", {}).get("concurrent_calls", 0)
            max_calls = 1000  # Configurable maximum
            
            # Adjust max based on current system performance
            cpu_percent = metrics.get("system", {}).get("cpu_percent", 0)
            memory_percent = metrics.get("system", {}).get("memory_percent", 0)
            
            # Reduce capacity if system is under stress
            if cpu_percent > 80 or memory_percent > 80:
                max_calls = int(max_calls * 0.8)
            elif cpu_percent > 60 or memory_percent > 60:
                max_calls = int(max_calls * 0.9)
            
            available_capacity = max(0, max_calls - current_calls)
            utilization = (current_calls / max_calls) * 100 if max_calls > 0 else 0
            
            # Estimate time to capacity based on trends
            estimated_time = await self._estimate_time_to_capacity(current_calls, max_calls)
            
            return SystemCapacity(
                max_concurrent_calls=max_calls,
                current_concurrent_calls=current_calls,
                available_capacity=available_capacity,
                utilization_percentage=utilization,
                estimated_time_to_capacity=estimated_time
            )
            
        except Exception as e:
            self.logger.error("Failed to get system capacity", error=str(e))
            return SystemCapacity(
                max_concurrent_calls=1000,
                current_concurrent_calls=0,
                available_capacity=1000,
                utilization_percentage=0.0,
                estimated_time_to_capacity=None
            )
    
    async def generate_scaling_recommendation(
        self,
        tenant_id: Optional[uuid.UUID] = None
    ) -> ScalingRecommendation:
        """
        Generate auto-scaling recommendation based on current metrics and trends.
        
        Args:
            tenant_id: Optional tenant ID
            
        Returns:
            ScalingRecommendation object
        """
        try:
            # Get current capacity and trends
            capacity = await self.get_system_capacity(tenant_id)
            trends = await self.analyze_performance_trends(tenant_id, hours=2)
            
            current_instances = 3  # Would be retrieved from orchestration system
            utilization = capacity.utilization_percentage / 100
            
            # Check cooldown period
            if self.last_scaling_action:
                time_since_last = datetime.utcnow() - self.last_scaling_action
                if time_since_last.total_seconds() < self.scaling_config["scale_up_cooldown"]:
                    return ScalingRecommendation(
                        action="maintain",
                        target_instances=current_instances,
                        current_instances=current_instances,
                        reason="Cooldown period active",
                        confidence=1.0
                    )
            
            # Determine scaling action
            if utilization >= self.scaling_config["scale_up_threshold"]:
                # Scale up
                target_instances = min(
                    current_instances + 1,
                    self.scaling_config["max_instances"]
                )
                
                confidence = min(1.0, utilization / self.scaling_config["scale_up_threshold"])
                
                return ScalingRecommendation(
                    action="scale_up",
                    target_instances=target_instances,
                    current_instances=current_instances,
                    reason=f"High utilization: {utilization:.1%}",
                    confidence=confidence
                )
            
            elif utilization <= self.scaling_config["scale_down_threshold"]:
                # Scale down
                target_instances = max(
                    current_instances - 1,
                    self.scaling_config["min_instances"]
                )
                
                confidence = min(1.0, (self.scaling_config["scale_down_threshold"] - utilization) / self.scaling_config["scale_down_threshold"])
                
                return ScalingRecommendation(
                    action="scale_down",
                    target_instances=target_instances,
                    current_instances=current_instances,
                    reason=f"Low utilization: {utilization:.1%}",
                    confidence=confidence
                )
            
            else:
                # Maintain current scale
                return ScalingRecommendation(
                    action="maintain",
                    target_instances=current_instances,
                    current_instances=current_instances,
                    reason=f"Optimal utilization: {utilization:.1%}",
                    confidence=0.8
                )
                
        except Exception as e:
            self.logger.error("Failed to generate scaling recommendation", error=str(e))
            return ScalingRecommendation(
                action="maintain",
                target_instances=1,
                current_instances=1,
                reason="Error in analysis",
                confidence=0.0
            )
    
    async def get_active_alerts(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[PerformanceAlert]:
        """
        Get active performance alerts.
        
        Args:
            tenant_id: Optional tenant ID filter
            severity: Optional severity filter
            
        Returns:
            List of active alerts
        """
        alerts = list(self.active_alerts.values())
        
        # Filter by tenant
        if tenant_id:
            alerts = [a for a in alerts if a.tenant_id == tenant_id]
        
        # Filter by severity
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Filter out resolved alerts
        alerts = [a for a in alerts if not a.resolved]
        
        return alerts
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as resolved.
        
        Args:
            alert_id: Alert ID to resolve
            
        Returns:
            True if resolved successfully
        """
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            return True
        return False
    
    # Private helper methods
    
    async def _collect_application_metrics(
        self,
        tenant_id: Optional[uuid.UUID]
    ) -> Dict[str, Any]:
        """Collect application-specific metrics."""
        try:
            # Mock application metrics (would be collected from actual app)
            return {
                "concurrent_calls": 150,  # Would be actual count
                "avg_response_time_ms": 250.0,
                "error_rate": 0.02,
                "requests_per_second": 45.0,
                "active_sessions": 75,
                "queue_length": 5
            }
        except Exception:
            return {}
    
    async def _collect_database_metrics(
        self,
        tenant_id: Optional[uuid.UUID]
    ) -> Dict[str, Any]:
        """Collect database performance metrics."""
        try:
            # Mock database metrics (would query actual DB stats)
            return {
                "avg_query_time_ms": 15.0,
                "active_connections": 25,
                "slow_queries": 2,
                "cache_hit_rate": 0.95,
                "disk_io_rate": 1024.0  # KB/s
            }
        except Exception:
            return {}
    
    async def _collect_external_service_metrics(self) -> Dict[str, Any]:
        """Collect external service metrics."""
        try:
            # Mock external service metrics
            return {
                "twilio_api_latency_ms": 120.0,
                "openai_api_latency_ms": 800.0,
                "twilio_success_rate": 0.998,
                "openai_success_rate": 0.995
            }
        except Exception:
            return {}
    
    async def _store_metrics_in_database(
        self,
        tenant_id: uuid.UUID,
        metrics: Dict[str, Any]
    ):
        """Store metrics in database for historical analysis."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                system_metrics = SystemMetrics(
                    tenant_id=tenant_id,
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.SYSTEM_PERFORMANCE,
                    concurrent_calls=metrics.get("application", {}).get("concurrent_calls", 0),
                    system_cpu_usage=metrics.get("system", {}).get("cpu_percent"),
                    system_memory_usage=metrics.get("system", {}).get("memory_percent"),
                    api_response_time_ms=metrics.get("application", {}).get("avg_response_time_ms"),
                    api_error_rate=metrics.get("application", {}).get("error_rate", 0.0),
                    database_query_time_ms=metrics.get("database", {}).get("avg_query_time_ms"),
                    metadata=metrics
                )
                
                session.add(system_metrics)
                await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to store metrics in database", error=str(e))
    
    def _calculate_metric_trend(
        self,
        metrics_list: List[Dict[str, Any]],
        metric_path: str
    ) -> Dict[str, Any]:
        """Calculate trend for a specific metric."""
        try:
            values = []
            timestamps = []
            
            for metric in metrics_list:
                # Navigate nested dict path
                value = metric
                for key in metric_path.split('.'):
                    value = value.get(key, {})
                
                if isinstance(value, (int, float)):
                    values.append(value)
                    timestamps.append(datetime.fromisoformat(metric["timestamp"]))
            
            if len(values) < 2:
                return {"trend": "insufficient_data", "values": values}
            
            # Calculate simple trend
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            
            change_percent = ((avg_second - avg_first) / avg_first * 100) if avg_first > 0 else 0
            
            if change_percent > 10:
                trend = "increasing"
            elif change_percent < -10:
                trend = "decreasing"
            else:
                trend = "stable"
            
            return {
                "trend": trend,
                "change_percent": change_percent,
                "current_value": values[-1],
                "average_value": sum(values) / len(values),
                "min_value": min(values),
                "max_value": max(values),
                "data_points": len(values)
            }
            
        except Exception:
            return {"trend": "error", "values": []}
    
    async def _analyze_capacity_trends(
        self,
        metrics_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze capacity trends."""
        try:
            concurrent_calls = [
                m.get("application", {}).get("concurrent_calls", 0)
                for m in metrics_list
            ]
            
            if not concurrent_calls:
                return {"trend": "no_data"}
            
            # Calculate growth rate
            if len(concurrent_calls) >= 2:
                recent_avg = sum(concurrent_calls[-10:]) / min(10, len(concurrent_calls))
                older_avg = sum(concurrent_calls[:10]) / min(10, len(concurrent_calls))
                
                growth_rate = (recent_avg - older_avg) / max(1, older_avg)
            else:
                growth_rate = 0
            
            return {
                "current_calls": concurrent_calls[-1],
                "peak_calls": max(concurrent_calls),
                "average_calls": sum(concurrent_calls) / len(concurrent_calls),
                "growth_rate": growth_rate,
                "trend": "growing" if growth_rate > 0.1 else "stable" if growth_rate > -0.1 else "declining"
            }
            
        except Exception:
            return {"trend": "error"}
    
    async def _generate_scaling_recommendation(
        self,
        trends: Dict[str, Any]
    ) -> ScalingRecommendation:
        """Generate scaling recommendation based on trends."""
        try:
            capacity_trend = trends.get("capacity", {})
            cpu_trend = trends.get("cpu", {})
            memory_trend = trends.get("memory", {})
            
            # Simple recommendation logic
            if (capacity_trend.get("trend") == "growing" and 
                cpu_trend.get("trend") == "increasing"):
                return ScalingRecommendation(
                    action="scale_up",
                    target_instances=4,
                    current_instances=3,
                    reason="Growing capacity demand and increasing CPU usage",
                    confidence=0.8
                )
            elif (capacity_trend.get("trend") == "declining" and 
                  cpu_trend.get("current_value", 0) < 30):
                return ScalingRecommendation(
                    action="scale_down",
                    target_instances=2,
                    current_instances=3,
                    reason="Declining capacity demand and low CPU usage",
                    confidence=0.7
                )
            else:
                return ScalingRecommendation(
                    action="maintain",
                    target_instances=3,
                    current_instances=3,
                    reason="Stable performance metrics",
                    confidence=0.6
                )
                
        except Exception:
            return ScalingRecommendation(
                action="maintain",
                target_instances=3,
                current_instances=3,
                reason="Error in trend analysis",
                confidence=0.0
            )
    
    async def _estimate_time_to_capacity(
        self,
        current_calls: int,
        max_calls: int
    ) -> Optional[int]:
        """Estimate time to reach capacity in minutes."""
        try:
            if len(self.performance_history) < 10:
                return None
            
            # Get recent call counts
            recent_calls = [
                m.get("application", {}).get("concurrent_calls", 0)
                for m in self.performance_history[-10:]
            ]
            
            # Calculate growth rate (calls per minute)
            if len(recent_calls) >= 2:
                time_diff = 10  # Assuming 1 minute between measurements
                call_diff = recent_calls[-1] - recent_calls[0]
                growth_rate = call_diff / time_diff
                
                if growth_rate > 0:
                    remaining_capacity = max_calls - current_calls
                    estimated_minutes = remaining_capacity / growth_rate
                    return int(estimated_minutes)
            
            return None
            
        except Exception:
            return None
    
    def _create_alert(
        self,
        alert_id: str,
        severity: AlertSeverity,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        message: str,
        tenant_id: Optional[uuid.UUID]
    ) -> PerformanceAlert:
        """Create a performance alert."""
        return PerformanceAlert(
            id=f"{alert_id}_{int(datetime.utcnow().timestamp())}",
            severity=severity,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            message=message,
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            resolved=False
        )


# Singleton instance
performance_monitoring_service = PerformanceMonitoringService()