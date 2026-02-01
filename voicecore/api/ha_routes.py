"""
High availability API routes for VoiceCore AI.

Provides endpoints for high availability management, failover control,
and health monitoring per Requirements 11.2 and 11.5.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from voicecore.services.high_availability_service import (
    HighAvailabilityService, ServiceEndpoint, ServiceStatus
)
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/ha", tags=["high-availability"])

# Initialize service
ha_service = HighAvailabilityService()


# Request/Response models
class ServiceEndpointRequest(BaseModel):
    """Request model for service endpoint configuration."""
    id: str = Field(..., description="Unique endpoint identifier")
    name: str = Field(..., description="Human-readable endpoint name")
    url: str = Field(..., description="Endpoint URL")
    region: str = Field(..., description="Geographic region")
    priority: int = Field(1, ge=1, le=100, description="Priority (lower = higher priority)")
    weight: int = Field(100, ge=1, le=1000, description="Load balancing weight")
    health_check_path: str = Field("/health", description="Health check path")
    timeout_seconds: int = Field(30, ge=5, le=300, description="Health check timeout")
    max_retries: int = Field(3, ge=1, le=10, description="Maximum retry attempts")


class ServiceEndpointResponse(BaseModel):
    """Response model for service endpoint."""
    id: str
    name: str
    url: str
    region: str
    priority: int
    weight: int
    health_check_path: str
    timeout_seconds: int
    max_retries: int
    status: Optional[str] = None
    last_check: Optional[str] = None
    response_time_ms: Optional[float] = None


class HealthStatusResponse(BaseModel):
    """Response model for health status."""
    overall_status: str
    total_endpoints: int
    healthy_endpoints: int
    degraded_endpoints: int
    unhealthy_endpoints: int
    active_endpoint: Optional[str]
    primary_endpoint: Optional[str]
    failover_enabled: bool
    load_balancer_enabled: bool
    endpoints: Dict[str, Any]


class HealthCheckResponse(BaseModel):
    """Response model for health check result."""
    endpoint_id: str
    status: str
    response_time_ms: float
    timestamp: str
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LoadBalancerConfigRequest(BaseModel):
    """Request model for load balancer configuration."""
    enabled: bool = Field(True, description="Enable load balancing")
    algorithm: str = Field("weighted_round_robin", description="Load balancing algorithm")


class FailoverConfigRequest(BaseModel):
    """Request model for failover configuration."""
    enabled: bool = Field(True, description="Enable automatic failover")
    threshold: int = Field(3, ge=1, le=10, description="Failure threshold for failover")


# Endpoint management
@router.get("/endpoints", response_model=List[ServiceEndpointResponse])
async def list_endpoints():
    """
    List all configured service endpoints.
    
    Returns all service endpoints with their current status.
    """
    try:
        health_status = ha_service.get_health_status()
        endpoints = []
        
        for endpoint_id, endpoint_info in health_status["endpoints"].items():
            endpoint = ha_service.endpoints[endpoint_id]
            
            endpoints.append(ServiceEndpointResponse(
                id=endpoint.id,
                name=endpoint.name,
                url=endpoint.url,
                region=endpoint.region,
                priority=endpoint.priority,
                weight=endpoint.weight,
                health_check_path=endpoint.health_check_path,
                timeout_seconds=endpoint.timeout_seconds,
                max_retries=endpoint.max_retries,
                status=endpoint_info.get("status"),
                last_check=endpoint_info.get("last_check"),
                response_time_ms=ha_service.health_results.get(endpoint_id, {}).response_time_ms if endpoint_id in ha_service.health_results else None
            ))
        
        return endpoints
        
    except Exception as e:
        logger.error("Failed to list endpoints", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve endpoints"
        )


@router.post("/endpoints", response_model=ServiceEndpointResponse)
async def add_endpoint(endpoint_request: ServiceEndpointRequest):
    """
    Add a new service endpoint.
    
    Registers a new service endpoint for high availability.
    """
    try:
        # Check if endpoint already exists
        if endpoint_request.id in ha_service.endpoints:
            raise HTTPException(
                status_code=400,
                detail=f"Endpoint with ID '{endpoint_request.id}' already exists"
            )
        
        # Create endpoint
        endpoint = ServiceEndpoint(
            id=endpoint_request.id,
            name=endpoint_request.name,
            url=endpoint_request.url,
            region=endpoint_request.region,
            priority=endpoint_request.priority,
            weight=endpoint_request.weight,
            health_check_path=endpoint_request.health_check_path,
            timeout_seconds=endpoint_request.timeout_seconds,
            max_retries=endpoint_request.max_retries
        )
        
        # Add endpoint
        ha_service.add_endpoint(endpoint)
        
        return ServiceEndpointResponse(
            id=endpoint.id,
            name=endpoint.name,
            url=endpoint.url,
            region=endpoint.region,
            priority=endpoint.priority,
            weight=endpoint.weight,
            health_check_path=endpoint.health_check_path,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add endpoint", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to add endpoint"
        )


@router.get("/endpoints/{endpoint_id}", response_model=ServiceEndpointResponse)
async def get_endpoint(endpoint_id: str):
    """
    Get details of a specific endpoint.
    
    Returns detailed information about the specified endpoint.
    """
    try:
        if endpoint_id not in ha_service.endpoints:
            raise HTTPException(
                status_code=404,
                detail="Endpoint not found"
            )
        
        endpoint = ha_service.endpoints[endpoint_id]
        health_result = ha_service.health_results.get(endpoint_id)
        
        return ServiceEndpointResponse(
            id=endpoint.id,
            name=endpoint.name,
            url=endpoint.url,
            region=endpoint.region,
            priority=endpoint.priority,
            weight=endpoint.weight,
            health_check_path=endpoint.health_check_path,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries,
            status=health_result.status.value if health_result else None,
            last_check=health_result.timestamp.isoformat() if health_result else None,
            response_time_ms=health_result.response_time_ms if health_result else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get endpoint", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve endpoint"
        )


@router.put("/endpoints/{endpoint_id}", response_model=ServiceEndpointResponse)
async def update_endpoint(endpoint_id: str, endpoint_request: ServiceEndpointRequest):
    """
    Update an existing service endpoint.
    
    Updates the configuration of the specified endpoint.
    """
    try:
        if endpoint_id not in ha_service.endpoints:
            raise HTTPException(
                status_code=404,
                detail="Endpoint not found"
            )
        
        # Remove old endpoint
        ha_service.remove_endpoint(endpoint_id)
        
        # Create updated endpoint
        endpoint = ServiceEndpoint(
            id=endpoint_request.id,
            name=endpoint_request.name,
            url=endpoint_request.url,
            region=endpoint_request.region,
            priority=endpoint_request.priority,
            weight=endpoint_request.weight,
            health_check_path=endpoint_request.health_check_path,
            timeout_seconds=endpoint_request.timeout_seconds,
            max_retries=endpoint_request.max_retries
        )
        
        # Add updated endpoint
        ha_service.add_endpoint(endpoint)
        
        return ServiceEndpointResponse(
            id=endpoint.id,
            name=endpoint.name,
            url=endpoint.url,
            region=endpoint.region,
            priority=endpoint.priority,
            weight=endpoint.weight,
            health_check_path=endpoint.health_check_path,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update endpoint", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to update endpoint"
        )


@router.delete("/endpoints/{endpoint_id}")
async def remove_endpoint(endpoint_id: str):
    """
    Remove a service endpoint.
    
    Removes the specified endpoint from high availability configuration.
    """
    try:
        success = ha_service.remove_endpoint(endpoint_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Endpoint not found"
            )
        
        return {
            "message": "Endpoint removed successfully",
            "endpoint_id": endpoint_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove endpoint", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to remove endpoint"
        )


# Health monitoring
@router.get("/health", response_model=HealthStatusResponse)
async def get_health_status():
    """
    Get overall health status.
    
    Returns comprehensive health status of all endpoints.
    """
    try:
        health_status = ha_service.get_health_status()
        
        return HealthStatusResponse(**health_status)
        
    except Exception as e:
        logger.error("Failed to get health status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve health status"
        )


@router.post("/health/check")
async def trigger_health_check():
    """
    Trigger immediate health check for all endpoints.
    
    Forces health check execution for all configured endpoints.
    """
    try:
        results = []
        
        for endpoint_id in ha_service.endpoints.keys():
            result = await ha_service.check_endpoint_health(endpoint_id)
            results.append(HealthCheckResponse(
                endpoint_id=result.endpoint_id,
                status=result.status.value,
                response_time_ms=result.response_time_ms,
                timestamp=result.timestamp.isoformat(),
                error_message=result.error_message,
                metadata=result.metadata
            ))
        
        return {
            "message": "Health check completed",
            "results": results
        }
        
    except Exception as e:
        logger.error("Failed to trigger health check", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to perform health check"
        )


@router.get("/health/{endpoint_id}", response_model=HealthCheckResponse)
async def check_endpoint_health(endpoint_id: str):
    """
    Check health of specific endpoint.
    
    Performs immediate health check for the specified endpoint.
    """
    try:
        if endpoint_id not in ha_service.endpoints:
            raise HTTPException(
                status_code=404,
                detail="Endpoint not found"
            )
        
        result = await ha_service.check_endpoint_health(endpoint_id)
        
        return HealthCheckResponse(
            endpoint_id=result.endpoint_id,
            status=result.status.value,
            response_time_ms=result.response_time_ms,
            timestamp=result.timestamp.isoformat(),
            error_message=result.error_message,
            metadata=result.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check endpoint health", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to check endpoint health"
        )


@router.post("/monitoring/start")
async def start_health_monitoring():
    """
    Start continuous health monitoring.
    
    Enables automatic health checking for all endpoints.
    """
    try:
        await ha_service.start_health_monitoring()
        
        return {
            "message": "Health monitoring started",
            "status": "active"
        }
        
    except Exception as e:
        logger.error("Failed to start health monitoring", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to start health monitoring"
        )


@router.post("/monitoring/stop")
async def stop_health_monitoring():
    """
    Stop continuous health monitoring.
    
    Disables automatic health checking.
    """
    try:
        await ha_service.stop_health_monitoring()
        
        return {
            "message": "Health monitoring stopped",
            "status": "inactive"
        }
        
    except Exception as e:
        logger.error("Failed to stop health monitoring", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to stop health monitoring"
        )


# Failover management
@router.get("/failover/history")
async def get_failover_history(
    hours: int = Query(24, ge=1, le=168, description="Hours of history")
):
    """
    Get failover event history.
    
    Returns recent failover events and their outcomes.
    """
    try:
        events = ha_service.get_failover_history(hours)
        
        return {
            "period": {
                "hours": hours,
                "events_count": len(events)
            },
            "events": events
        }
        
    except Exception as e:
        logger.error("Failed to get failover history", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve failover history"
        )


@router.post("/failover/config")
async def configure_failover(config: FailoverConfigRequest):
    """
    Configure failover settings.
    
    Updates automatic failover configuration.
    """
    try:
        ha_service.failover_enabled = config.enabled
        ha_service.failover_threshold = config.threshold
        
        return {
            "message": "Failover configuration updated",
            "config": {
                "enabled": config.enabled,
                "threshold": config.threshold
            }
        }
        
    except Exception as e:
        logger.error("Failed to configure failover", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to configure failover"
        )


@router.get("/active-endpoint")
async def get_active_endpoint():
    """
    Get currently active endpoint.
    
    Returns the endpoint currently handling requests.
    """
    try:
        active_endpoint = await ha_service.get_active_endpoint()
        
        if not active_endpoint:
            return {
                "active_endpoint": None,
                "message": "No active endpoint available"
            }
        
        return {
            "active_endpoint": {
                "id": active_endpoint.id,
                "name": active_endpoint.name,
                "url": active_endpoint.url,
                "region": active_endpoint.region,
                "priority": active_endpoint.priority
            }
        }
        
    except Exception as e:
        logger.error("Failed to get active endpoint", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve active endpoint"
        )


# Load balancing
@router.get("/load-balancer/stats")
async def get_load_balancer_stats():
    """
    Get load balancer statistics.
    
    Returns load balancing performance and distribution stats.
    """
    try:
        stats = ha_service.get_load_balancer_stats()
        
        return {
            "message": "Load balancer statistics retrieved",
            "stats": stats
        }
        
    except Exception as e:
        logger.error("Failed to get load balancer stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve load balancer statistics"
        )


@router.post("/load-balancer/config")
async def configure_load_balancer(config: LoadBalancerConfigRequest):
    """
    Configure load balancer settings.
    
    Updates load balancing configuration.
    """
    try:
        # Validate algorithm
        valid_algorithms = ["round_robin", "weighted_round_robin", "least_connections"]
        if config.algorithm not in valid_algorithms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid algorithm. Must be one of: {valid_algorithms}"
            )
        
        ha_service.load_balancer_enabled = config.enabled
        ha_service.load_balancer_algorithm = config.algorithm
        
        return {
            "message": "Load balancer configuration updated",
            "config": {
                "enabled": config.enabled,
                "algorithm": config.algorithm
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to configure load balancer", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to configure load balancer"
        )


@router.get("/select-endpoint")
async def select_endpoint_for_request():
    """
    Select endpoint for new request.
    
    Returns the best endpoint for handling a new request based on load balancing.
    """
    try:
        selected_endpoint = await ha_service.select_endpoint_for_request()
        
        if not selected_endpoint:
            return {
                "selected_endpoint": None,
                "message": "No endpoints available"
            }
        
        return {
            "selected_endpoint": {
                "id": selected_endpoint.id,
                "name": selected_endpoint.name,
                "url": selected_endpoint.url,
                "region": selected_endpoint.region,
                "weight": selected_endpoint.weight
            }
        }
        
    except Exception as e:
        logger.error("Failed to select endpoint", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to select endpoint"
        )


# Health check endpoint
@router.get("/service-health")
async def ha_service_health():
    """
    Health check for high availability service.
    
    Returns health status of the HA service itself.
    """
    try:
        health_status = ha_service.get_health_status()
        
        return {
            "status": "healthy",
            "service": "high-availability",
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_active": ha_service.health_check_task and not ha_service.health_check_task.done(),
            "total_endpoints": health_status["total_endpoints"],
            "healthy_endpoints": health_status["healthy_endpoints"]
        }
        
    except Exception as e:
        logger.error("HA service health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "high-availability",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }