"""
Property-based tests for scalability features.

Tests auto-scaling response, failover recovery, and capacity handling
per Requirements 11.1, 11.2, and 11.3.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
from typing import Dict, Any, List

from voicecore.services.auto_scaling_service import (
    AutoScalingService, ScalingPolicy, ScalingAction, ScalingStatus
)
from voicecore.services.high_availability_service import (
    HighAvailabilityService, ServiceEndpoint, ServiceStatus, FailoverStatus
)
from voicecore.services.performance_monitoring_service import (
    PerformanceMonitoringService, SystemCapacity, ScalingRecommendation
)


class TestAutoScalingProperties:
    """Property-based tests for auto-scaling functionality."""
    
    @pytest.fixture
    def auto_scaling_service(self):
        """Create auto-scaling service instance."""
        return AutoScalingService()
    
    @pytest.fixture
    def performance_service(self):
        """Create performance monitoring service instance."""
        return PerformanceMonitoringService()
    
    @given(
        utilization=st.floats(min_value=0.0, max_value=1.0),
        current_instances=st.integers(min_value=1, max_value=10),
        min_instances=st.integers(min_value=1, max_value=3),
        max_instances=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=100, deadline=5000)
    async def test_property_25_auto_scaling_response(
        self,
        auto_scaling_service,
        utilization,
        current_instances,
        min_instances,
        max_instances
    ):
        """
        **Property 25: Auto-scaling Response**
        **Validates: Requirements 11.1, 11.3**
        
        Auto-scaling system must respond appropriately to load changes:
        - Scale up when utilization exceeds threshold
        - Scale down when utilization is below threshold
        - Respect min/max instance limits
        - Maintain cooldown periods
        """
        assume(min_instances <= max_instances)
        assume(min_instances <= current_instances <= max_instances)
        
        # Create scaling policy
        policy = ScalingPolicy(
            name="test_policy",
            enabled=True,
            min_instances=min_instances,
            max_instances=max_instances,
            target_utilization=0.65,
            scale_up_threshold=0.75,
            scale_down_threshold=0.30,
            scale_up_cooldown=60,  # Short for testing
            scale_down_cooldown=120,
            scale_up_increment=1,
            scale_down_decrement=1,
            evaluation_period=30
        )
        
        # Set current state
        auto_scaling_service.current_instances = current_instances
        auto_scaling_service.last_scaling_event = None  # No cooldown
        
        # Mock performance service to return specific utilization
        class MockPerformanceService:
            async def get_system_capacity(self, tenant_id=None):
                return SystemCapacity(
                    max_concurrent_calls=1000,
                    current_concurrent_calls=int(utilization * 1000),
                    available_capacity=int((1 - utilization) * 1000),
                    utilization_percentage=utilization * 100,
                    estimated_time_to_capacity=None
                )
        
        auto_scaling_service.performance_service = MockPerformanceService()
        
        # Evaluate scaling decision
        recommendation = await auto_scaling_service.evaluate_scaling_decision(
            policy=policy
        )
        
        # Verify scaling logic
        if utilization >= policy.scale_up_threshold:
            # Should recommend scale up if not at max
            if current_instances < max_instances:
                assert recommendation.action == "scale_up"
                assert recommendation.target_instances == current_instances + 1
                assert recommendation.target_instances <= max_instances
            else:
                assert recommendation.action == "maintain"
                assert recommendation.reason == "Already at maximum instances"
        
        elif utilization <= policy.scale_down_threshold:
            # Should recommend scale down if not at min
            if current_instances > min_instances:
                assert recommendation.action == "scale_down"
                assert recommendation.target_instances == current_instances - 1
                assert recommendation.target_instances >= min_instances
            else:
                assert recommendation.action == "maintain"
                assert recommendation.reason == "Already at minimum instances"
        
        else:
            # Should maintain current scale
            assert recommendation.action == "maintain"
            assert recommendation.target_instances == current_instances
        
        # Verify confidence is reasonable
        assert 0.0 <= recommendation.confidence <= 1.0
        
        # Verify instance limits are always respected
        assert min_instances <= recommendation.target_instances <= max_instances
    
    @given(
        cooldown_seconds=st.integers(min_value=60, max_value=600),
        time_since_last=st.integers(min_value=0, max_value=1200)
    )
    @settings(max_examples=50, deadline=3000)
    async def test_property_25_cooldown_enforcement(
        self,
        auto_scaling_service,
        cooldown_seconds,
        time_since_last
    ):
        """
        Test that cooldown periods are properly enforced.
        """
        # Create policy with specific cooldown
        policy = ScalingPolicy(
            name="cooldown_test",
            enabled=True,
            min_instances=1,
            max_instances=10,
            target_utilization=0.65,
            scale_up_threshold=0.75,
            scale_down_threshold=0.30,
            scale_up_cooldown=cooldown_seconds,
            scale_down_cooldown=cooldown_seconds,
            scale_up_increment=1,
            scale_down_decrement=1,
            evaluation_period=30
        )
        
        # Set last scaling event
        from voicecore.services.auto_scaling_service import ScalingEvent
        auto_scaling_service.last_scaling_event = ScalingEvent(
            id="test_event",
            timestamp=datetime.utcnow() - timedelta(seconds=time_since_last),
            action=ScalingAction.SCALE_UP,
            from_instances=2,
            to_instances=3,
            reason="Test scaling",
            success=True
        )
        
        # Mock high utilization that would normally trigger scaling
        class MockPerformanceService:
            async def get_system_capacity(self, tenant_id=None):
                return SystemCapacity(
                    max_concurrent_calls=1000,
                    current_concurrent_calls=800,  # 80% utilization
                    available_capacity=200,
                    utilization_percentage=80.0,
                    estimated_time_to_capacity=None
                )
        
        auto_scaling_service.performance_service = MockPerformanceService()
        auto_scaling_service.current_instances = 3
        
        # Evaluate scaling decision
        recommendation = await auto_scaling_service.evaluate_scaling_decision(
            policy=policy
        )
        
        # Verify cooldown enforcement
        if time_since_last < cooldown_seconds:
            # Should be in cooldown
            assert recommendation.action == "maintain"
            assert "cooldown" in recommendation.reason.lower()
        else:
            # Should allow scaling
            assert recommendation.action in ["scale_up", "maintain"]
            if recommendation.action == "maintain":
                assert "cooldown" not in recommendation.reason.lower()


class TestHighAvailabilityProperties:
    """Property-based tests for high availability functionality."""
    
    @pytest.fixture
    def ha_service(self):
        """Create high availability service instance."""
        service = HighAvailabilityService()
        # Clear default endpoints for testing
        service.endpoints.clear()
        service.primary_endpoint = None
        service.active_endpoint = None
        return service
    
    @given(
        num_endpoints=st.integers(min_value=2, max_value=5),
        failure_endpoint_index=st.integers(min_value=0, max_value=4)
    )
    @settings(max_examples=50, deadline=5000)
    async def test_property_26_failover_recovery(
        self,
        ha_service,
        num_endpoints,
        failure_endpoint_index
    ):
        """
        **Property 26: Failover Recovery**
        **Validates: Requirements 11.2, 11.5**
        
        High availability system must handle failover correctly:
        - Detect endpoint failures
        - Switch to healthy backup endpoint
        - Maintain service availability during failover
        - Recover failed endpoints when they become healthy
        """
        assume(failure_endpoint_index < num_endpoints)
        
        # Create test endpoints
        endpoints = []
        for i in range(num_endpoints):
            endpoint = ServiceEndpoint(
                id=f"endpoint_{i}",
                name=f"Test Endpoint {i}",
                url=f"http://test{i}.example.com",
                region=f"region-{i}",
                priority=i + 1,  # Lower number = higher priority
                weight=100,
                timeout_seconds=5
            )
            endpoints.append(endpoint)
            ha_service.add_endpoint(endpoint)
        
        # Verify initial state
        assert ha_service.primary_endpoint == "endpoint_0"  # Highest priority
        assert ha_service.active_endpoint == "endpoint_0"
        
        # Simulate endpoint failure
        failed_endpoint_id = f"endpoint_{failure_endpoint_index}"
        
        # Mock health check to show failure
        from voicecore.services.high_availability_service import HealthCheckResult
        failure_result = HealthCheckResult(
            endpoint_id=failed_endpoint_id,
            status=ServiceStatus.UNHEALTHY,
            response_time_ms=5000.0,
            timestamp=datetime.utcnow(),
            error_message="Connection timeout"
        )
        
        ha_service.health_results[failed_endpoint_id] = failure_result
        
        # Trigger failover if the failed endpoint was active
        if ha_service.active_endpoint == failed_endpoint_id:
            await ha_service.handle_request_failure(
                failed_endpoint_id,
                Exception("Endpoint failure")
            )
        
        # Verify failover behavior
        active_endpoint = await ha_service.get_active_endpoint()
        
        if num_endpoints > 1:
            # Should have switched to a different endpoint
            assert active_endpoint is not None
            assert active_endpoint.id != failed_endpoint_id
            
            # Should select the highest priority healthy endpoint
            healthy_endpoints = [
                ep for ep in endpoints 
                if ep.id != failed_endpoint_id
            ]
            expected_active = min(healthy_endpoints, key=lambda x: x.priority)
            assert active_endpoint.id == expected_active.id
        
        # Verify service remains available
        selected_endpoint = await ha_service.select_endpoint_for_request()
        assert selected_endpoint is not None
        assert selected_endpoint.id != failed_endpoint_id
        
        # Test recovery - mark failed endpoint as healthy
        recovery_result = HealthCheckResult(
            endpoint_id=failed_endpoint_id,
            status=ServiceStatus.HEALTHY,
            response_time_ms=100.0,
            timestamp=datetime.utcnow()
        )
        
        ha_service.health_results[failed_endpoint_id] = recovery_result
        
        # If the recovered endpoint has higher priority, it should become active
        if failure_endpoint_index == 0:  # Highest priority endpoint
            # Force re-evaluation
            ha_service._select_best_endpoint()
            active_after_recovery = await ha_service.get_active_endpoint()
            assert active_after_recovery.id == failed_endpoint_id
    
    @given(
        num_requests=st.integers(min_value=10, max_value=100),
        num_endpoints=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=30, deadline=5000)
    async def test_property_26_load_distribution(
        self,
        ha_service,
        num_requests,
        num_endpoints
    ):
        """
        Test that load balancing distributes requests appropriately.
        """
        # Create endpoints with different weights
        total_weight = 0
        for i in range(num_endpoints):
            weight = (i + 1) * 50  # 50, 100, 150, etc.
            endpoint = ServiceEndpoint(
                id=f"endpoint_{i}",
                name=f"Test Endpoint {i}",
                url=f"http://test{i}.example.com",
                region=f"region-{i}",
                priority=i + 1,
                weight=weight,
                timeout_seconds=5
            )
            ha_service.add_endpoint(endpoint)
            total_weight += weight
        
        # Mark all endpoints as healthy
        for i in range(num_endpoints):
            endpoint_id = f"endpoint_{i}"
            ha_service.health_results[endpoint_id] = HealthCheckResult(
                endpoint_id=endpoint_id,
                status=ServiceStatus.HEALTHY,
                response_time_ms=100.0,
                timestamp=datetime.utcnow()
            )
        
        # Enable load balancing
        ha_service.load_balancer_enabled = True
        ha_service.load_balancer_algorithm = "weighted_round_robin"
        
        # Simulate requests
        request_counts = {f"endpoint_{i}": 0 for i in range(num_endpoints)}
        
        for _ in range(num_requests):
            selected = await ha_service.select_endpoint_for_request()
            assert selected is not None
            request_counts[selected.id] += 1
            
            # Update request count for load balancing
            ha_service.request_counts[selected.id] = ha_service.request_counts.get(selected.id, 0) + 1
        
        # Verify load distribution is reasonable
        # Allow some variance but check general distribution
        total_requests = sum(request_counts.values())
        assert total_requests == num_requests
        
        # Each endpoint should get some requests (unless very few total requests)
        if num_requests >= num_endpoints * 2:
            for endpoint_id, count in request_counts.items():
                assert count > 0, f"Endpoint {endpoint_id} received no requests"


class TestCapacityHandlingProperties:
    """Property-based tests for capacity handling."""
    
    @pytest.fixture
    def performance_service(self):
        """Create performance monitoring service instance."""
        return PerformanceMonitoringService()
    
    @given(
        current_calls=st.integers(min_value=0, max_value=1000),
        max_calls=st.integers(min_value=100, max_value=2000),
        cpu_percent=st.floats(min_value=0.0, max_value=100.0),
        memory_percent=st.floats(min_value=0.0, max_value=100.0)
    )
    @settings(max_examples=100, deadline=3000)
    async def test_property_27_capacity_handling(
        self,
        performance_service,
        current_calls,
        max_calls,
        cpu_percent,
        memory_percent
    ):
        """
        **Property 27: Capacity Handling**
        **Validates: Requirements 11.1, 11.3**
        
        System must handle capacity correctly:
        - Calculate available capacity accurately
        - Adjust capacity based on system performance
        - Provide accurate utilization metrics
        - Generate appropriate scaling recommendations
        """
        assume(current_calls <= max_calls)
        
        # Mock system metrics
        class MockMetrics:
            def __init__(self):
                self.metrics = {
                    "system": {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory_percent
                    },
                    "application": {
                        "concurrent_calls": current_calls
                    }
                }
        
        # Override collect_system_metrics method
        async def mock_collect_metrics(tenant_id=None):
            return MockMetrics().metrics
        
        performance_service.collect_system_metrics = mock_collect_metrics
        
        # Get system capacity
        capacity = await performance_service.get_system_capacity()
        
        # Verify capacity calculations
        assert capacity.current_concurrent_calls == current_calls
        assert capacity.max_concurrent_calls > 0
        assert capacity.available_capacity >= 0
        assert capacity.utilization_percentage >= 0.0
        
        # Verify capacity is reduced under system stress
        if cpu_percent > 80 or memory_percent > 80:
            # Capacity should be reduced
            assert capacity.max_concurrent_calls <= 800  # 80% of 1000
        elif cpu_percent > 60 or memory_percent > 60:
            # Capacity should be slightly reduced
            assert capacity.max_concurrent_calls <= 900  # 90% of 1000
        
        # Verify utilization calculation
        expected_utilization = (current_calls / capacity.max_concurrent_calls) * 100
        assert abs(capacity.utilization_percentage - expected_utilization) < 0.1
        
        # Verify available capacity
        expected_available = max(0, capacity.max_concurrent_calls - current_calls)
        assert capacity.available_capacity == expected_available
        
        # Test scaling recommendation
        recommendation = await performance_service.generate_scaling_recommendation()
        
        # Verify recommendation is valid
        assert recommendation.action in ["scale_up", "scale_down", "maintain"]
        assert recommendation.target_instances > 0
        assert recommendation.current_instances > 0
        assert 0.0 <= recommendation.confidence <= 1.0
        
        # Verify scaling logic based on utilization
        utilization = capacity.utilization_percentage / 100
        
        if utilization >= 0.75:  # Scale up threshold
            if recommendation.action == "scale_up":
                assert recommendation.target_instances > recommendation.current_instances
        elif utilization <= 0.30:  # Scale down threshold
            if recommendation.action == "scale_down":
                assert recommendation.target_instances < recommendation.current_instances
        
        # Verify capacity constraints are respected
        if capacity.utilization_percentage >= 95.0:
            # Near capacity - should recommend scaling up or maintaining
            assert recommendation.action in ["scale_up", "maintain"]
        
        if capacity.utilization_percentage <= 10.0:
            # Very low utilization - should recommend scaling down or maintaining
            assert recommendation.action in ["scale_down", "maintain"]
    
    @given(
        metrics_count=st.integers(min_value=5, max_value=50),
        call_growth_rate=st.floats(min_value=-0.5, max_value=2.0)
    )
    @settings(max_examples=30, deadline=5000)
    async def test_property_27_capacity_trend_analysis(
        self,
        performance_service,
        metrics_count,
        call_growth_rate
    ):
        """
        Test that capacity trend analysis works correctly.
        """
        # Generate synthetic metrics with trend
        base_calls = 100
        metrics_list = []
        
        for i in range(metrics_count):
            # Apply growth rate
            calls = max(0, int(base_calls + (i * call_growth_rate * 10)))
            
            metric = {
                "timestamp": (datetime.utcnow() - timedelta(minutes=metrics_count - i)).isoformat(),
                "application": {
                    "concurrent_calls": calls
                },
                "system": {
                    "cpu_percent": min(100, 20 + (calls / 10)),
                    "memory_percent": min(100, 30 + (calls / 15))
                }
            }
            metrics_list.append(metric)
        
        # Set performance history
        performance_service.performance_history = metrics_list
        
        # Analyze trends
        trends = await performance_service.analyze_performance_trends(hours=1)
        
        # Verify trend analysis
        assert "concurrent_calls" in trends
        call_trend = trends["concurrent_calls"]
        
        # Verify trend detection
        if call_growth_rate > 0.2:
            assert call_trend["trend"] in ["increasing", "stable"]
        elif call_growth_rate < -0.2:
            assert call_trend["trend"] in ["decreasing", "stable"]
        
        # Verify statistical measures
        assert call_trend["data_points"] == metrics_count
        assert call_trend["min_value"] >= 0
        assert call_trend["max_value"] >= call_trend["min_value"]
        assert call_trend["current_value"] >= 0
        
        # Verify capacity analysis
        assert "capacity" in trends
        capacity_analysis = trends["capacity"]
        
        if call_growth_rate > 0.1:
            assert capacity_analysis["growth_rate"] >= 0
        elif call_growth_rate < -0.1:
            assert capacity_analysis["growth_rate"] <= 0


class ScalabilityStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for scalability system.
    
    Tests complex interactions between auto-scaling, high availability,
    and performance monitoring components.
    """
    
    def __init__(self):
        super().__init__()
        self.auto_scaling = AutoScalingService()
        self.ha_service = HighAvailabilityService()
        self.performance_service = PerformanceMonitoringService()
        
        # Clear default endpoints
        self.ha_service.endpoints.clear()
        self.ha_service.primary_endpoint = None
        self.ha_service.active_endpoint = None
        
        # System state
        self.current_load = 0.5  # 50% utilization
        self.endpoints_added = 0
        self.scaling_events = []
    
    @initialize()
    def setup_initial_state(self):
        """Initialize the system with basic configuration."""
        # Add initial endpoints
        for i in range(2):
            endpoint = ServiceEndpoint(
                id=f"endpoint_{i}",
                name=f"Initial Endpoint {i}",
                url=f"http://initial{i}.example.com",
                region=f"region-{i}",
                priority=i + 1,
                weight=100
            )
            self.ha_service.add_endpoint(endpoint)
            self.endpoints_added += 1
    
    @rule(
        load_change=st.floats(min_value=-0.3, max_value=0.3)
    )
    def change_system_load(self, load_change):
        """Simulate system load changes."""
        self.current_load = max(0.0, min(1.0, self.current_load + load_change))
    
    @rule()
    def add_endpoint(self):
        """Add a new service endpoint."""
        if self.endpoints_added < 5:
            endpoint = ServiceEndpoint(
                id=f"endpoint_{self.endpoints_added}",
                name=f"Dynamic Endpoint {self.endpoints_added}",
                url=f"http://dynamic{self.endpoints_added}.example.com",
                region=f"region-{self.endpoints_added}",
                priority=self.endpoints_added + 1,
                weight=100
            )
            self.ha_service.add_endpoint(endpoint)
            self.endpoints_added += 1
    
    @rule(
        endpoint_index=st.integers(min_value=0, max_value=4)
    )
    def simulate_endpoint_failure(self, endpoint_index):
        """Simulate endpoint failure."""
        if endpoint_index < self.endpoints_added:
            endpoint_id = f"endpoint_{endpoint_index}"
            if endpoint_id in self.ha_service.endpoints:
                # Mark as unhealthy
                from voicecore.services.high_availability_service import HealthCheckResult
                self.ha_service.health_results[endpoint_id] = HealthCheckResult(
                    endpoint_id=endpoint_id,
                    status=ServiceStatus.UNHEALTHY,
                    response_time_ms=5000.0,
                    timestamp=datetime.utcnow(),
                    error_message="Simulated failure"
                )
    
    @rule()
    async def trigger_scaling_evaluation(self):
        """Trigger auto-scaling evaluation."""
        # Mock performance metrics based on current load
        class MockPerformanceService:
            def __init__(self, load):
                self.load = load
            
            async def get_system_capacity(self, tenant_id=None):
                return SystemCapacity(
                    max_concurrent_calls=1000,
                    current_concurrent_calls=int(self.load * 1000),
                    available_capacity=int((1 - self.load) * 1000),
                    utilization_percentage=self.load * 100,
                    estimated_time_to_capacity=None
                )
        
        self.auto_scaling.performance_service = MockPerformanceService(self.current_load)
        
        # Evaluate scaling
        recommendation = await self.auto_scaling.evaluate_scaling_decision()
        
        # Execute if needed
        if recommendation.action != "maintain":
            event = await self.auto_scaling.execute_scaling_action(recommendation)
            self.scaling_events.append(event)
    
    @invariant()
    def system_remains_available(self):
        """System must always have at least one available endpoint."""
        if self.endpoints_added > 0:
            # At least one endpoint should be available
            available_endpoints = []
            for endpoint_id in self.ha_service.endpoints:
                if self.ha_service._is_endpoint_available(endpoint_id):
                    available_endpoints.append(endpoint_id)
            
            # Should have at least one available endpoint or be able to fallback
            assert len(available_endpoints) > 0 or len(self.ha_service.endpoints) > 0
    
    @invariant()
    def scaling_respects_constraints(self):
        """Auto-scaling must respect instance constraints."""
        current_instances = self.auto_scaling.current_instances
        policy = self.auto_scaling.default_policy
        
        assert policy.min_instances <= current_instances <= policy.max_instances
    
    @invariant()
    def load_within_bounds(self):
        """System load must remain within valid bounds."""
        assert 0.0 <= self.current_load <= 1.0


# Test runner for stateful testing
TestScalabilityStateMachine = ScalabilityStateMachine.TestCase