"""
High availability service for VoiceCore AI.

Implements automatic failover mechanisms, load balancing,
and health checks per Requirements 11.2 and 11.5.
"""

import uuid
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class FailoverStatus(Enum):
    """Failover status."""
    ACTIVE = "active"
    STANDBY = "standby"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""
    id: str
    name: str
    url: str
    region: str
    priority: int  # Lower number = higher priority
    weight: int  # For load balancing
    health_check_path: str = "/health"
    timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class HealthCheckResult:
    """Health check result."""
    endpoint_id: str
    status: ServiceStatus
    response_time_ms: float
    timestamp: datetime
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FailoverEvent:
    """Failover event record."""
    id: str
    timestamp: datetime
    from_endpoint: str
    to_endpoint: str
    reason: str
    success: bool
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class LoadBalancerStats:
    """Load balancer statistics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: float
    requests_per_endpoint: Dict[str, int]
    error_rate: float


class HighAvailabilityService:
    """
    Comprehensive high availability service.
    
    Implements automatic failover, load balancing, and health monitoring
    per Requirements 11.2 and 11.5.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Service endpoints configuration
        self.endpoints: Dict[str, ServiceEndpoint] = {}
        self.primary_endpoint: Optional[str] = None
        self.active_endpoint: Optional[str] = None
        
        # Health monitoring
        self.health_results: Dict[str, HealthCheckResult] = {}
        self.health_check_interval = 30  # seconds
        self.health_check_task = None
        
        # Failover configuration
        self.failover_enabled = True
        self.failover_threshold = 3  # consecutive failures
        self.failover_events: List[FailoverEvent] = []
        
        # Load balancing
        self.load_balancer_enabled = True
        self.load_balancer_algorithm = "weighted_round_robin"
        self.current_endpoint_index = 0
        self.request_counts: Dict[str, int] = {}
        
        # Circuit breaker
        self.circuit_breaker_enabled = True
        self.circuit_breaker_threshold = 5  # failures
        self.circuit_breaker_timeout = 60  # seconds
        self.circuit_breaker_state: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self.stats = LoadBalancerStats(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            average_response_time_ms=0.0,
            requests_per_endpoint={},
            error_rate=0.0
        )
        
        # Initialize default endpoints
        self._initialize_default_endpoints()
    
    def add_endpoint(self, endpoint: ServiceEndpoint):
        """
        Add a service endpoint.
        
        Args:
            endpoint: ServiceEndpoint configuration
        """
        self.endpoints[endpoint.id] = endpoint
        self.request_counts[endpoint.id] = 0
        self.stats.requests_per_endpoint[endpoint.id] = 0
        
        # Set as primary if it's the first or highest priority
        if (not self.primary_endpoint or 
            endpoint.priority < self.endpoints[self.primary_endpoint].priority):
            self.primary_endpoint = endpoint.id
            if not self.active_endpoint:
                self.active_endpoint = endpoint.id
        
        self.logger.info(
            "Service endpoint added",
            endpoint_id=endpoint.id,
            name=endpoint.name,
            url=endpoint.url,
            region=endpoint.region,
            priority=endpoint.priority
        )
    
    def remove_endpoint(self, endpoint_id: str) -> bool:
        """
        Remove a service endpoint.
        
        Args:
            endpoint_id: Endpoint ID to remove
            
        Returns:
            True if removed successfully
        """
        if endpoint_id not in self.endpoints:
            return False
        
        # Switch active endpoint if removing the active one
        if self.active_endpoint == endpoint_id:
            self._select_best_endpoint()
        
        # Switch primary endpoint if removing the primary one
        if self.primary_endpoint == endpoint_id:
            self.primary_endpoint = None
            for ep_id, endpoint in self.endpoints.items():
                if ep_id != endpoint_id:
                    if (not self.primary_endpoint or 
                        endpoint.priority < self.endpoints[self.primary_endpoint].priority):
                        self.primary_endpoint = ep_id
        
        # Clean up
        del self.endpoints[endpoint_id]
        self.request_counts.pop(endpoint_id, None)
        self.stats.requests_per_endpoint.pop(endpoint_id, None)
        self.health_results.pop(endpoint_id, None)
        self.circuit_breaker_state.pop(endpoint_id, None)
        
        self.logger.info("Service endpoint removed", endpoint_id=endpoint_id)
        return True
    
    async def start_health_monitoring(self):
        """Start health check monitoring for all endpoints."""
        if self.health_check_task and not self.health_check_task.done():
            return
        
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_health_monitoring(self):
        """Stop health check monitoring."""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Health monitoring stopped")
    
    async def check_endpoint_health(self, endpoint_id: str) -> HealthCheckResult:
        """
        Check health of a specific endpoint.
        
        Args:
            endpoint_id: Endpoint ID to check
            
        Returns:
            HealthCheckResult object
        """
        if endpoint_id not in self.endpoints:
            return HealthCheckResult(
                endpoint_id=endpoint_id,
                status=ServiceStatus.UNKNOWN,
                response_time_ms=0.0,
                timestamp=datetime.utcnow(),
                error_message="Endpoint not found"
            )
        
        endpoint = self.endpoints[endpoint_id]
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=endpoint.timeout_seconds)
            ) as session:
                health_url = f"{endpoint.url.rstrip('/')}{endpoint.health_check_path}"
                
                async with session.get(health_url) as response:
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    
                    if response.status == 200:
                        try:
                            health_data = await response.json()
                            status = ServiceStatus.HEALTHY
                            metadata = health_data
                        except:
                            status = ServiceStatus.HEALTHY
                            metadata = {"status_code": response.status}
                    elif 200 <= response.status < 300:
                        status = ServiceStatus.HEALTHY
                        metadata = {"status_code": response.status}
                    elif 500 <= response.status < 600:
                        status = ServiceStatus.UNHEALTHY
                        metadata = {"status_code": response.status}
                    else:
                        status = ServiceStatus.DEGRADED
                        metadata = {"status_code": response.status}
                    
                    result = HealthCheckResult(
                        endpoint_id=endpoint_id,
                        status=status,
                        response_time_ms=response_time,
                        timestamp=start_time,
                        metadata=metadata
                    )
                    
        except asyncio.TimeoutError:
            result = HealthCheckResult(
                endpoint_id=endpoint_id,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=endpoint.timeout_seconds * 1000,
                timestamp=start_time,
                error_message="Health check timeout"
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            result = HealthCheckResult(
                endpoint_id=endpoint_id,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=start_time,
                error_message=str(e)
            )
        
        # Store result
        self.health_results[endpoint_id] = result
        
        # Update circuit breaker state
        self._update_circuit_breaker(endpoint_id, result.status == ServiceStatus.HEALTHY)
        
        return result
    
    async def get_active_endpoint(self) -> Optional[ServiceEndpoint]:
        """
        Get the currently active endpoint.
        
        Returns:
            Active ServiceEndpoint or None
        """
        if not self.active_endpoint or self.active_endpoint not in self.endpoints:
            self._select_best_endpoint()
        
        return self.endpoints.get(self.active_endpoint)
    
    async def select_endpoint_for_request(self) -> Optional[ServiceEndpoint]:
        """
        Select best endpoint for a new request using load balancing.
        
        Returns:
            Selected ServiceEndpoint or None
        """
        if not self.endpoints:
            return None
        
        if not self.load_balancer_enabled:
            return await self.get_active_endpoint()
        
        # Get healthy endpoints
        healthy_endpoints = []
        for endpoint_id, endpoint in self.endpoints.items():
            if self._is_endpoint_available(endpoint_id):
                healthy_endpoints.append(endpoint)
        
        if not healthy_endpoints:
            # Fallback to any endpoint if none are healthy
            healthy_endpoints = list(self.endpoints.values())
        
        # Apply load balancing algorithm
        if self.load_balancer_algorithm == "round_robin":
            selected = self._round_robin_selection(healthy_endpoints)
        elif self.load_balancer_algorithm == "weighted_round_robin":
            selected = self._weighted_round_robin_selection(healthy_endpoints)
        elif self.load_balancer_algorithm == "least_connections":
            selected = self._least_connections_selection(healthy_endpoints)
        else:
            # Default to weighted round robin
            selected = self._weighted_round_robin_selection(healthy_endpoints)
        
        return selected
    
    async def handle_request_failure(
        self,
        endpoint_id: str,
        error: Exception
    ):
        """
        Handle request failure and potentially trigger failover.
        
        Args:
            endpoint_id: Failed endpoint ID
            error: Exception that occurred
        """
        self.stats.failed_requests += 1
        
        # Update circuit breaker
        self._update_circuit_breaker(endpoint_id, False)
        
        # Check if failover is needed
        if (self.failover_enabled and 
            endpoint_id == self.active_endpoint and
            self._should_trigger_failover(endpoint_id)):
            
            await self._trigger_failover(endpoint_id, str(error))
    
    async def handle_request_success(
        self,
        endpoint_id: str,
        response_time_ms: float
    ):
        """
        Handle successful request.
        
        Args:
            endpoint_id: Successful endpoint ID
            response_time_ms: Response time in milliseconds
        """
        self.stats.successful_requests += 1
        self.stats.requests_per_endpoint[endpoint_id] += 1
        
        # Update average response time
        total_requests = self.stats.successful_requests + self.stats.failed_requests
        if total_requests > 0:
            self.stats.average_response_time_ms = (
                (self.stats.average_response_time_ms * (total_requests - 1) + response_time_ms) / 
                total_requests
            )
            self.stats.error_rate = self.stats.failed_requests / total_requests
        
        # Update circuit breaker
        self._update_circuit_breaker(endpoint_id, True)
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of all endpoints.
        
        Returns:
            Dict containing health status information
        """
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        
        for result in self.health_results.values():
            if result.status == ServiceStatus.HEALTHY:
                healthy_count += 1
            elif result.status == ServiceStatus.DEGRADED:
                degraded_count += 1
            elif result.status == ServiceStatus.UNHEALTHY:
                unhealthy_count += 1
        
        total_endpoints = len(self.endpoints)
        
        if total_endpoints == 0:
            overall_status = ServiceStatus.UNKNOWN
        elif unhealthy_count == total_endpoints:
            overall_status = ServiceStatus.UNHEALTHY
        elif healthy_count == total_endpoints:
            overall_status = ServiceStatus.HEALTHY
        else:
            overall_status = ServiceStatus.DEGRADED
        
        return {
            "overall_status": overall_status.value,
            "total_endpoints": total_endpoints,
            "healthy_endpoints": healthy_count,
            "degraded_endpoints": degraded_count,
            "unhealthy_endpoints": unhealthy_count,
            "active_endpoint": self.active_endpoint,
            "primary_endpoint": self.primary_endpoint,
            "failover_enabled": self.failover_enabled,
            "load_balancer_enabled": self.load_balancer_enabled,
            "endpoints": {
                endpoint_id: {
                    "name": endpoint.name,
                    "url": endpoint.url,
                    "region": endpoint.region,
                    "priority": endpoint.priority,
                    "status": self.health_results.get(endpoint_id, {}).status.value if endpoint_id in self.health_results else "unknown",
                    "last_check": self.health_results.get(endpoint_id, {}).timestamp.isoformat() if endpoint_id in self.health_results else None,
                    "circuit_breaker": self.circuit_breaker_state.get(endpoint_id, {})
                }
                for endpoint_id, endpoint in self.endpoints.items()
            }
        }
    
    def get_failover_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get failover event history.
        
        Args:
            hours: Hours of history to retrieve
            
        Returns:
            List of failover events
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        events = [
            {
                "id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "from_endpoint": event.from_endpoint,
                "to_endpoint": event.to_endpoint,
                "reason": event.reason,
                "success": event.success,
                "duration_seconds": event.duration_seconds,
                "error_message": event.error_message
            }
            for event in self.failover_events
            if event.timestamp > cutoff_time
        ]
        
        return sorted(events, key=lambda x: x["timestamp"], reverse=True)
    
    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """
        Get load balancer statistics.
        
        Returns:
            Dict containing load balancer stats
        """
        return {
            "algorithm": self.load_balancer_algorithm,
            "enabled": self.load_balancer_enabled,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "error_rate": self.stats.error_rate,
            "average_response_time_ms": self.stats.average_response_time_ms,
            "requests_per_endpoint": self.stats.requests_per_endpoint
        }
    
    # Private helper methods
    
    def _initialize_default_endpoints(self):
        """Initialize default service endpoints."""
        # This would be configured based on deployment
        default_endpoints = [
            ServiceEndpoint(
                id="primary",
                name="Primary Region",
                url="http://localhost:8000",
                region="us-east-1",
                priority=1,
                weight=100
            ),
            ServiceEndpoint(
                id="secondary",
                name="Secondary Region",
                url="http://localhost:8001",
                region="us-west-2",
                priority=2,
                weight=50
            )
        ]
        
        for endpoint in default_endpoints:
            self.add_endpoint(endpoint)
    
    async def _health_check_loop(self):
        """Main health check monitoring loop."""
        while True:
            try:
                # Check all endpoints
                tasks = [
                    self.check_endpoint_health(endpoint_id)
                    for endpoint_id in self.endpoints.keys()
                ]
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check if active endpoint needs to be changed
                if not self._is_endpoint_available(self.active_endpoint):
                    self._select_best_endpoint()
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in health check loop", error=str(e))
                await asyncio.sleep(self.health_check_interval)
    
    def _is_endpoint_available(self, endpoint_id: Optional[str]) -> bool:
        """Check if endpoint is available (healthy and not circuit broken)."""
        if not endpoint_id or endpoint_id not in self.endpoints:
            return False
        
        # Check health status
        if endpoint_id in self.health_results:
            health_result = self.health_results[endpoint_id]
            if health_result.status == ServiceStatus.UNHEALTHY:
                return False
        
        # Check circuit breaker
        if endpoint_id in self.circuit_breaker_state:
            cb_state = self.circuit_breaker_state[endpoint_id]
            if cb_state.get("state") == "open":
                return False
        
        return True
    
    def _select_best_endpoint(self):
        """Select the best available endpoint as active."""
        # Find the highest priority healthy endpoint
        best_endpoint = None
        best_priority = float('inf')
        
        for endpoint_id, endpoint in self.endpoints.items():
            if (self._is_endpoint_available(endpoint_id) and 
                endpoint.priority < best_priority):
                best_endpoint = endpoint_id
                best_priority = endpoint.priority
        
        # If no healthy endpoint, use primary
        if not best_endpoint:
            best_endpoint = self.primary_endpoint
        
        if best_endpoint != self.active_endpoint:
            old_endpoint = self.active_endpoint
            self.active_endpoint = best_endpoint
            
            self.logger.info(
                "Active endpoint changed",
                from_endpoint=old_endpoint,
                to_endpoint=best_endpoint
            )
    
    def _should_trigger_failover(self, endpoint_id: str) -> bool:
        """Check if failover should be triggered for endpoint."""
        if endpoint_id not in self.health_results:
            return False
        
        # Check consecutive failures
        # This is simplified - in production, you'd track failure history
        health_result = self.health_results[endpoint_id]
        return health_result.status == ServiceStatus.UNHEALTHY
    
    async def _trigger_failover(self, failed_endpoint_id: str, reason: str):
        """Trigger failover from failed endpoint."""
        start_time = datetime.utcnow()
        event_id = str(uuid.uuid4())
        
        # Select new endpoint
        old_active = self.active_endpoint
        self._select_best_endpoint()
        new_active = self.active_endpoint
        
        success = new_active != failed_endpoint_id
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Record failover event
        event = FailoverEvent(
            id=event_id,
            timestamp=start_time,
            from_endpoint=failed_endpoint_id,
            to_endpoint=new_active or "none",
            reason=reason,
            success=success,
            duration_seconds=duration,
            error_message=None if success else "No healthy endpoints available"
        )
        
        self.failover_events.append(event)
        
        # Keep only last 100 events
        if len(self.failover_events) > 100:
            self.failover_events = self.failover_events[-100:]
        
        self.logger.info(
            "Failover triggered",
            event_id=event_id,
            from_endpoint=failed_endpoint_id,
            to_endpoint=new_active,
            success=success,
            reason=reason
        )
    
    def _update_circuit_breaker(self, endpoint_id: str, success: bool):
        """Update circuit breaker state for endpoint."""
        if not self.circuit_breaker_enabled:
            return
        
        if endpoint_id not in self.circuit_breaker_state:
            self.circuit_breaker_state[endpoint_id] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": None,
                "next_attempt": None
            }
        
        cb_state = self.circuit_breaker_state[endpoint_id]
        
        if success:
            # Reset on success
            cb_state["failure_count"] = 0
            if cb_state["state"] == "half_open":
                cb_state["state"] = "closed"
        else:
            # Increment failure count
            cb_state["failure_count"] += 1
            cb_state["last_failure"] = datetime.utcnow()
            
            # Open circuit breaker if threshold reached
            if (cb_state["failure_count"] >= self.circuit_breaker_threshold and
                cb_state["state"] == "closed"):
                cb_state["state"] = "open"
                cb_state["next_attempt"] = datetime.utcnow() + timedelta(seconds=self.circuit_breaker_timeout)
        
        # Check if circuit breaker should move to half-open
        if (cb_state["state"] == "open" and 
            cb_state["next_attempt"] and
            datetime.utcnow() >= cb_state["next_attempt"]):
            cb_state["state"] = "half_open"
    
    def _round_robin_selection(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Round robin endpoint selection."""
        if not endpoints:
            return None
        
        self.current_endpoint_index = (self.current_endpoint_index + 1) % len(endpoints)
        return endpoints[self.current_endpoint_index]
    
    def _weighted_round_robin_selection(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Weighted round robin endpoint selection."""
        if not endpoints:
            return None
        
        # Simple weighted selection based on weight
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return endpoints[0]
        
        # Use request count to implement weighted round robin
        min_ratio = float('inf')
        selected = endpoints[0]
        
        for endpoint in endpoints:
            current_requests = self.request_counts.get(endpoint.id, 0)
            expected_ratio = endpoint.weight / total_weight
            actual_ratio = current_requests / max(1, sum(self.request_counts.values()))
            
            if actual_ratio < expected_ratio and actual_ratio < min_ratio:
                min_ratio = actual_ratio
                selected = endpoint
        
        return selected
    
    def _least_connections_selection(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Least connections endpoint selection."""
        if not endpoints:
            return None
        
        # Use request count as proxy for connections
        min_requests = float('inf')
        selected = endpoints[0]
        
        for endpoint in endpoints:
            requests = self.request_counts.get(endpoint.id, 0)
            if requests < min_requests:
                min_requests = requests
                selected = endpoint
        
        return selected


# Singleton instance
high_availability_service = HighAvailabilityService()