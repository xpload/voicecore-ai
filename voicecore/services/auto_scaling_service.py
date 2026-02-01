"""
Auto-scaling service for VoiceCore AI.

Implements load-based auto-scaling with performance monitoring
and capacity management per Requirements 11.1 and 11.3.
"""

import uuid
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from voicecore.services.performance_monitoring_service import (
    PerformanceMonitoringService, ScalingRecommendation, SystemCapacity
)
from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class ScalingAction(Enum):
    """Auto-scaling actions."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    MAINTAIN = "maintain"


class ScalingStatus(Enum):
    """Auto-scaling status."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    COOLDOWN = "cooldown"
    ERROR = "error"


@dataclass
class ScalingEvent:
    """Auto-scaling event record."""
    id: str
    timestamp: datetime
    action: ScalingAction
    from_instances: int
    to_instances: int
    reason: str
    success: bool
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class ScalingPolicy:
    """Auto-scaling policy configuration."""
    name: str
    enabled: bool
    min_instances: int
    max_instances: int
    target_utilization: float
    scale_up_threshold: float
    scale_down_threshold: float
    scale_up_cooldown: int  # seconds
    scale_down_cooldown: int  # seconds
    scale_up_increment: int
    scale_down_decrement: int
    evaluation_period: int  # seconds


class AutoScalingService:
    """
    Comprehensive auto-scaling service.
    
    Implements load-based auto-scaling with performance monitoring
    per Requirements 11.1 and 11.3.
    """
    
    def __init__(self):
        self.logger = logger
        self.performance_service = PerformanceMonitoringService()
        
        # Auto-scaling state
        self.status = ScalingStatus.ENABLED
        self.current_instances = 3  # Would be retrieved from orchestration
        self.last_scaling_event = None
        
        # Scaling history
        self.scaling_events: List[ScalingEvent] = []
        
        # Default scaling policy
        self.default_policy = ScalingPolicy(
            name="default",
            enabled=True,
            min_instances=1,
            max_instances=10,
            target_utilization=0.65,
            scale_up_threshold=0.75,
            scale_down_threshold=0.30,
            scale_up_cooldown=300,  # 5 minutes
            scale_down_cooldown=600,  # 10 minutes
            scale_up_increment=1,
            scale_down_decrement=1,
            evaluation_period=60  # 1 minute
        )
        
        # Tenant-specific policies
        self.tenant_policies: Dict[str, ScalingPolicy] = {}
        
        # Scaling callbacks (for integration with orchestration systems)
        self.scaling_callbacks: List[Callable] = []
        
        # Monitoring task
        self.monitoring_task = None
    
    async def start_auto_scaling(self):
        """Start the auto-scaling monitoring loop."""
        if self.monitoring_task and not self.monitoring_task.done():
            return
        
        self.status = ScalingStatus.ENABLED
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("Auto-scaling service started")
    
    async def stop_auto_scaling(self):
        """Stop the auto-scaling monitoring loop."""
        self.status = ScalingStatus.DISABLED
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Auto-scaling service stopped")
    
    async def evaluate_scaling_decision(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        policy: Optional[ScalingPolicy] = None
    ) -> ScalingRecommendation:
        """
        Evaluate whether scaling action is needed.
        
        Args:
            tenant_id: Optional tenant ID
            policy: Optional custom scaling policy
            
        Returns:
            ScalingRecommendation object
        """
        try:
            # Use provided policy or get tenant-specific/default policy
            if not policy:
                policy = self._get_scaling_policy(tenant_id)
            
            if not policy.enabled:
                return ScalingRecommendation(
                    action="maintain",
                    target_instances=self.current_instances,
                    current_instances=self.current_instances,
                    reason="Auto-scaling disabled",
                    confidence=1.0
                )
            
            # Check cooldown period
            if self._is_in_cooldown(policy):
                return ScalingRecommendation(
                    action="maintain",
                    target_instances=self.current_instances,
                    current_instances=self.current_instances,
                    reason="Cooldown period active",
                    confidence=1.0
                )
            
            # Get current system metrics
            capacity = await self.performance_service.get_system_capacity(tenant_id)
            utilization = capacity.utilization_percentage / 100
            
            # Evaluate scaling decision
            if utilization >= policy.scale_up_threshold:
                # Scale up needed
                target_instances = min(
                    self.current_instances + policy.scale_up_increment,
                    policy.max_instances
                )
                
                if target_instances > self.current_instances:
                    confidence = min(1.0, utilization / policy.scale_up_threshold)
                    return ScalingRecommendation(
                        action="scale_up",
                        target_instances=target_instances,
                        current_instances=self.current_instances,
                        reason=f"High utilization: {utilization:.1%} >= {policy.scale_up_threshold:.1%}",
                        confidence=confidence
                    )
                else:
                    return ScalingRecommendation(
                        action="maintain",
                        target_instances=self.current_instances,
                        current_instances=self.current_instances,
                        reason="Already at maximum instances",
                        confidence=1.0
                    )
            
            elif utilization <= policy.scale_down_threshold:
                # Scale down needed
                target_instances = max(
                    self.current_instances - policy.scale_down_decrement,
                    policy.min_instances
                )
                
                if target_instances < self.current_instances:
                    confidence = min(1.0, (policy.scale_down_threshold - utilization) / policy.scale_down_threshold)
                    return ScalingRecommendation(
                        action="scale_down",
                        target_instances=target_instances,
                        current_instances=self.current_instances,
                        reason=f"Low utilization: {utilization:.1%} <= {policy.scale_down_threshold:.1%}",
                        confidence=confidence
                    )
                else:
                    return ScalingRecommendation(
                        action="maintain",
                        target_instances=self.current_instances,
                        current_instances=self.current_instances,
                        reason="Already at minimum instances",
                        confidence=1.0
                    )
            
            else:
                # No scaling needed
                return ScalingRecommendation(
                    action="maintain",
                    target_instances=self.current_instances,
                    current_instances=self.current_instances,
                    reason=f"Utilization within target range: {utilization:.1%}",
                    confidence=0.8
                )
                
        except Exception as e:
            self.logger.error("Failed to evaluate scaling decision", error=str(e))
            return ScalingRecommendation(
                action="maintain",
                target_instances=self.current_instances,
                current_instances=self.current_instances,
                reason=f"Error in evaluation: {str(e)}",
                confidence=0.0
            )
    
    async def execute_scaling_action(
        self,
        recommendation: ScalingRecommendation,
        tenant_id: Optional[uuid.UUID] = None
    ) -> ScalingEvent:
        """
        Execute a scaling action based on recommendation.
        
        Args:
            recommendation: Scaling recommendation to execute
            tenant_id: Optional tenant ID
            
        Returns:
            ScalingEvent record
        """
        event_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            if recommendation.action == "maintain":
                # No action needed
                event = ScalingEvent(
                    id=event_id,
                    timestamp=start_time,
                    action=ScalingAction.MAINTAIN,
                    from_instances=self.current_instances,
                    to_instances=self.current_instances,
                    reason=recommendation.reason,
                    success=True,
                    duration_seconds=0.0
                )
                
                self.scaling_events.append(event)
                return event
            
            # Execute scaling action
            action = ScalingAction.SCALE_UP if recommendation.action == "scale_up" else ScalingAction.SCALE_DOWN
            
            self.logger.info(
                f"Executing scaling action: {action.value}",
                from_instances=self.current_instances,
                to_instances=recommendation.target_instances,
                reason=recommendation.reason
            )
            
            # Call scaling callbacks (integration with orchestration systems)
            success = await self._execute_scaling_callbacks(
                action, self.current_instances, recommendation.target_instances
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            if success:
                # Update current instance count
                old_instances = self.current_instances
                self.current_instances = recommendation.target_instances
                
                event = ScalingEvent(
                    id=event_id,
                    timestamp=start_time,
                    action=action,
                    from_instances=old_instances,
                    to_instances=self.current_instances,
                    reason=recommendation.reason,
                    success=True,
                    duration_seconds=duration
                )
                
                self.last_scaling_event = event
                self.logger.info(
                    f"Scaling action completed successfully",
                    action=action.value,
                    instances=self.current_instances,
                    duration=duration
                )
            else:
                event = ScalingEvent(
                    id=event_id,
                    timestamp=start_time,
                    action=action,
                    from_instances=self.current_instances,
                    to_instances=recommendation.target_instances,
                    reason=recommendation.reason,
                    success=False,
                    duration_seconds=duration,
                    error_message="Scaling callback failed"
                )
                
                self.logger.error(
                    f"Scaling action failed",
                    action=action.value,
                    duration=duration
                )
            
            self.scaling_events.append(event)
            
            # Keep only last 100 events
            if len(self.scaling_events) > 100:
                self.scaling_events = self.scaling_events[-100:]
            
            return event
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            event = ScalingEvent(
                id=event_id,
                timestamp=start_time,
                action=ScalingAction.MAINTAIN,
                from_instances=self.current_instances,
                to_instances=self.current_instances,
                reason=recommendation.reason,
                success=False,
                duration_seconds=duration,
                error_message=str(e)
            )
            
            self.scaling_events.append(event)
            self.logger.error("Failed to execute scaling action", error=str(e))
            
            return event
    
    def set_scaling_policy(
        self,
        policy: ScalingPolicy,
        tenant_id: Optional[uuid.UUID] = None
    ):
        """
        Set scaling policy for tenant or default.
        
        Args:
            policy: Scaling policy to set
            tenant_id: Optional tenant ID (None for default)
        """
        if tenant_id:
            self.tenant_policies[str(tenant_id)] = policy
        else:
            self.default_policy = policy
        
        self.logger.info(
            "Scaling policy updated",
            tenant_id=str(tenant_id) if tenant_id else "default",
            policy_name=policy.name
        )
    
    def get_scaling_policy(
        self,
        tenant_id: Optional[uuid.UUID] = None
    ) -> ScalingPolicy:
        """
        Get scaling policy for tenant or default.
        
        Args:
            tenant_id: Optional tenant ID
            
        Returns:
            ScalingPolicy object
        """
        return self._get_scaling_policy(tenant_id)
    
    def add_scaling_callback(self, callback: Callable):
        """
        Add callback function for scaling actions.
        
        Args:
            callback: Async function to call during scaling
        """
        self.scaling_callbacks.append(callback)
    
    def get_scaling_history(
        self,
        hours: int = 24,
        tenant_id: Optional[uuid.UUID] = None
    ) -> List[ScalingEvent]:
        """
        Get scaling event history.
        
        Args:
            hours: Hours of history to retrieve
            tenant_id: Optional tenant ID filter
            
        Returns:
            List of scaling events
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        events = [
            event for event in self.scaling_events
            if event.timestamp > cutoff_time
        ]
        
        return sorted(events, key=lambda x: x.timestamp, reverse=True)
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """
        Get current auto-scaling status.
        
        Returns:
            Dict containing scaling status information
        """
        return {
            "status": self.status.value,
            "current_instances": self.current_instances,
            "last_scaling_event": {
                "timestamp": self.last_scaling_event.timestamp.isoformat() if self.last_scaling_event else None,
                "action": self.last_scaling_event.action.value if self.last_scaling_event else None,
                "success": self.last_scaling_event.success if self.last_scaling_event else None
            } if self.last_scaling_event else None,
            "policy": {
                "min_instances": self.default_policy.min_instances,
                "max_instances": self.default_policy.max_instances,
                "target_utilization": self.default_policy.target_utilization,
                "enabled": self.default_policy.enabled
            },
            "total_scaling_events": len(self.scaling_events),
            "monitoring_active": self.monitoring_task and not self.monitoring_task.done()
        }
    
    async def force_scaling_evaluation(
        self,
        tenant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Force immediate scaling evaluation and action.
        
        Args:
            tenant_id: Optional tenant ID
            
        Returns:
            Dict containing evaluation results
        """
        try:
            recommendation = await self.evaluate_scaling_decision(tenant_id)
            
            if recommendation.action != "maintain":
                event = await self.execute_scaling_action(recommendation, tenant_id)
                
                return {
                    "evaluation_performed": True,
                    "recommendation": {
                        "action": recommendation.action,
                        "target_instances": recommendation.target_instances,
                        "reason": recommendation.reason,
                        "confidence": recommendation.confidence
                    },
                    "scaling_event": {
                        "id": event.id,
                        "success": event.success,
                        "duration_seconds": event.duration_seconds,
                        "error_message": event.error_message
                    }
                }
            else:
                return {
                    "evaluation_performed": True,
                    "recommendation": {
                        "action": recommendation.action,
                        "reason": recommendation.reason,
                        "confidence": recommendation.confidence
                    },
                    "scaling_event": None
                }
                
        except Exception as e:
            self.logger.error("Failed to force scaling evaluation", error=str(e))
            return {
                "evaluation_performed": False,
                "error": str(e)
            }
    
    # Private helper methods
    
    async def _monitoring_loop(self):
        """Main monitoring loop for auto-scaling."""
        while self.status == ScalingStatus.ENABLED:
            try:
                # Evaluate scaling decision
                recommendation = await self.evaluate_scaling_decision()
                
                # Execute scaling action if needed
                if recommendation.action != "maintain":
                    await self.execute_scaling_action(recommendation)
                
                # Wait for next evaluation
                await asyncio.sleep(self.default_policy.evaluation_period)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in auto-scaling monitoring loop", error=str(e))
                await asyncio.sleep(60)  # Wait before retrying
    
    def _get_scaling_policy(
        self,
        tenant_id: Optional[uuid.UUID]
    ) -> ScalingPolicy:
        """Get scaling policy for tenant or default."""
        if tenant_id and str(tenant_id) in self.tenant_policies:
            return self.tenant_policies[str(tenant_id)]
        return self.default_policy
    
    def _is_in_cooldown(self, policy: ScalingPolicy) -> bool:
        """Check if scaling is in cooldown period."""
        if not self.last_scaling_event:
            return False
        
        time_since_last = datetime.utcnow() - self.last_scaling_event.timestamp
        
        if self.last_scaling_event.action == ScalingAction.SCALE_UP:
            return time_since_last.total_seconds() < policy.scale_up_cooldown
        elif self.last_scaling_event.action == ScalingAction.SCALE_DOWN:
            return time_since_last.total_seconds() < policy.scale_down_cooldown
        
        return False
    
    async def _execute_scaling_callbacks(
        self,
        action: ScalingAction,
        from_instances: int,
        to_instances: int
    ) -> bool:
        """Execute scaling callbacks."""
        try:
            for callback in self.scaling_callbacks:
                await callback(action, from_instances, to_instances)
            return True
        except Exception as e:
            self.logger.error("Scaling callback failed", error=str(e))
            return False


# Singleton instance
auto_scaling_service = AutoScalingService()