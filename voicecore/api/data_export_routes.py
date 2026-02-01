"""
API routes for data export and external integrations.

Provides REST API endpoints for data export in standard formats
and external integration management per Requirements 10.1 and 10.4.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator

from voicecore.services.data_export_service import (
    data_export_service, ExportFormat, DataType
)
from voicecore.services.auth_service import get_current_tenant
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Data Export & Integration"])


# Request/Response Models

class CreateExportRequest(BaseModel):
    """Request model for creating data export."""
    data_type: str = Field(..., description="Type of data to export")
    format: str = Field(..., description="Export format")
    filters: Optional[Dict[str, Any]] = Field(None, description="Data filters")
    start_date: Optional[datetime] = Field(None, description="Start date for data range")
    end_date: Optional[datetime] = Field(None, description="End date for data range")
    
    @validator('data_type')
    def validate_data_type(cls, v):
        try:
            DataType(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid data type. Must be one of: {[dt.value for dt in DataType]}")
    
    @validator('format')
    def validate_format(cls, v):
        try:
            ExportFormat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid format. Must be one of: {[fmt.value for fmt in ExportFormat]}")


class CreateIntegrationEndpointRequest(BaseModel):
    """Request model for creating integration endpoint."""
    name: str = Field(..., description="Endpoint name")
    endpoint_url: str = Field(..., description="Endpoint URL")
    auth_type: str = Field(..., description="Authentication type")
    auth_credentials: Dict[str, str] = Field(..., description="Authentication credentials")
    data_types: List[str] = Field(..., description="Supported data types")
    webhook_events: Optional[List[str]] = Field(None, description="Webhook events to subscribe to")
    
    @validator('auth_type')
    def validate_auth_type(cls, v):
        valid_types = ["api_key", "bearer", "basic", "none"]
        if v not in valid_types:
            raise ValueError(f"Invalid auth type. Must be one of: {valid_types}")
        return v
    
    @validator('data_types')
    def validate_data_types(cls, v):
        for data_type in v:
            try:
                DataType(data_type)
            except ValueError:
                raise ValueError(f"Invalid data type: {data_type}")
        return v


class UpdateIntegrationEndpointRequest(BaseModel):
    """Request model for updating integration endpoint."""
    name: Optional[str] = Field(None, description="Endpoint name")
    endpoint_url: Optional[str] = Field(None, description="Endpoint URL")
    auth_type: Optional[str] = Field(None, description="Authentication type")
    auth_credentials: Optional[Dict[str, str]] = Field(None, description="Authentication credentials")
    data_types: Optional[List[str]] = Field(None, description="Supported data types")
    webhook_events: Optional[List[str]] = Field(None, description="Webhook events")
    is_active: Optional[bool] = Field(None, description="Whether endpoint is active")


# Data Export Endpoints

@router.post("/export")
async def create_data_export(
    request: CreateExportRequest,
    background_tasks: BackgroundTasks,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Create a new data export request.
    
    Initiates data export in the specified format with optional filters
    and date range. The export is processed asynchronously.
    """
    try:
        # Prepare date range
        date_range = None
        if request.start_date or request.end_date:
            end_date = request.end_date or datetime.utcnow()
            start_date = request.start_date or (end_date - timedelta(days=30))
            date_range = {"start": start_date, "end": end_date}
        
        # Create export request
        export_request = await data_export_service.create_export_request(
            tenant_id=tenant_id,
            data_type=DataType(request.data_type),
            format=ExportFormat(request.format),
            filters=request.filters or {},
            date_range=date_range
        )
        
        return {
            "success": True,
            "export_request": {
                "id": export_request.id,
                "data_type": export_request.data_type.value,
                "format": export_request.format.value,
                "status": export_request.status,
                "created_at": export_request.created_at.isoformat(),
                "filters": export_request.filters,
                "date_range": {
                    "start": export_request.date_range["start"].isoformat(),
                    "end": export_request.date_range["end"].isoformat()
                }
            }
        }
        
    except Exception as e:
        logger.error("Failed to create data export", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create data export")


@router.get("/export/{export_id}")
async def get_export_status(
    export_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get the status of a data export request.
    
    Returns detailed information about the export request including
    status, progress, and download information when completed.
    """
    try:
        export_request = await data_export_service.get_export_request(
            request_id=export_id,
            tenant_id=tenant_id
        )
        
        if not export_request:
            raise HTTPException(status_code=404, detail="Export request not found")
        
        response = {
            "success": True,
            "export_request": {
                "id": export_request.id,
                "data_type": export_request.data_type.value,
                "format": export_request.format.value,
                "status": export_request.status,
                "created_at": export_request.created_at.isoformat(),
                "filters": export_request.filters,
                "date_range": {
                    "start": export_request.date_range["start"].isoformat(),
                    "end": export_request.date_range["end"].isoformat()
                }
            }
        }
        
        # Add completion details if available
        if export_request.completed_at:
            response["export_request"]["completed_at"] = export_request.completed_at.isoformat()
        
        if export_request.file_path:
            response["export_request"]["file_path"] = export_request.file_path
            response["export_request"]["file_size"] = export_request.file_size
        
        if export_request.error_message:
            response["export_request"]["error_message"] = export_request.error_message
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get export status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get export status")


@router.get("/exports")
async def list_export_requests(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of requests to return"),
    offset: int = Query(0, ge=0, description="Number of requests to skip")
):
    """
    List data export requests for the tenant.
    
    Returns a paginated list of export requests with their current status
    and basic information.
    """
    try:
        export_requests = await data_export_service.list_export_requests(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "total_requests": len(export_requests),
            "limit": limit,
            "offset": offset,
            "export_requests": [
                {
                    "id": req.id,
                    "data_type": req.data_type.value,
                    "format": req.format.value,
                    "status": req.status,
                    "created_at": req.created_at.isoformat(),
                    "completed_at": req.completed_at.isoformat() if req.completed_at else None,
                    "file_size": req.file_size
                }
                for req in export_requests
            ]
        }
        
    except Exception as e:
        logger.error("Failed to list export requests", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list export requests")


# Integration Endpoints Management

@router.post("/integrations")
async def create_integration_endpoint(
    request: CreateIntegrationEndpointRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Create a new external integration endpoint.
    
    Configures an external system integration with authentication
    and data type specifications for automated data synchronization.
    """
    try:
        # Convert string data types to enum
        data_types = [DataType(dt) for dt in request.data_types]
        
        endpoint = await data_export_service.create_integration_endpoint(
            tenant_id=tenant_id,
            name=request.name,
            endpoint_url=request.endpoint_url,
            auth_type=request.auth_type,
            auth_credentials=request.auth_credentials,
            data_types=data_types,
            webhook_events=request.webhook_events or []
        )
        
        return {
            "success": True,
            "integration_endpoint": {
                "id": endpoint.id,
                "name": endpoint.name,
                "endpoint_url": endpoint.endpoint_url,
                "auth_type": endpoint.auth_type,
                "data_types": [dt.value for dt in endpoint.data_types],
                "webhook_events": endpoint.webhook_events,
                "is_active": endpoint.is_active,
                "created_at": endpoint.created_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Failed to create integration endpoint", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create integration endpoint")


@router.get("/integrations/{endpoint_id}")
async def get_integration_endpoint(
    endpoint_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get details of a specific integration endpoint.
    
    Returns complete configuration and status information
    for the specified integration endpoint.
    """
    try:
        endpoint = await data_export_service.get_integration_endpoint(
            endpoint_id=endpoint_id,
            tenant_id=tenant_id
        )
        
        if not endpoint:
            raise HTTPException(status_code=404, detail="Integration endpoint not found")
        
        return {
            "success": True,
            "integration_endpoint": {
                "id": endpoint.id,
                "name": endpoint.name,
                "endpoint_url": endpoint.endpoint_url,
                "auth_type": endpoint.auth_type,
                "auth_credentials": endpoint.auth_credentials,
                "data_types": [dt.value for dt in endpoint.data_types],
                "webhook_events": endpoint.webhook_events,
                "is_active": endpoint.is_active,
                "created_at": endpoint.created_at.isoformat(),
                "last_sync": endpoint.last_sync.isoformat() if endpoint.last_sync else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get integration endpoint", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get integration endpoint")


@router.get("/integrations")
async def list_integration_endpoints(
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    List all integration endpoints for the tenant.
    
    Returns a list of configured integration endpoints with
    their current status and basic configuration.
    """
    try:
        endpoints = await data_export_service.list_integration_endpoints(
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "total_endpoints": len(endpoints),
            "integration_endpoints": [
                {
                    "id": endpoint.id,
                    "name": endpoint.name,
                    "endpoint_url": endpoint.endpoint_url,
                    "auth_type": endpoint.auth_type,
                    "data_types": [dt.value for dt in endpoint.data_types],
                    "webhook_events": endpoint.webhook_events,
                    "is_active": endpoint.is_active,
                    "created_at": endpoint.created_at.isoformat(),
                    "last_sync": endpoint.last_sync.isoformat() if endpoint.last_sync else None
                }
                for endpoint in endpoints
            ]
        }
        
    except Exception as e:
        logger.error("Failed to list integration endpoints", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list integration endpoints")


@router.put("/integrations/{endpoint_id}")
async def update_integration_endpoint(
    endpoint_id: str,
    request: UpdateIntegrationEndpointRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Update an existing integration endpoint.
    
    Updates configuration settings for an integration endpoint
    including authentication, data types, and webhook events.
    """
    try:
        # Prepare updates dictionary
        updates = {}
        
        if request.name is not None:
            updates["name"] = request.name
        
        if request.endpoint_url is not None:
            updates["endpoint_url"] = request.endpoint_url
        
        if request.auth_type is not None:
            updates["auth_type"] = request.auth_type
        
        if request.auth_credentials is not None:
            updates["auth_credentials"] = request.auth_credentials
        
        if request.data_types is not None:
            updates["data_types"] = [DataType(dt) for dt in request.data_types]
        
        if request.webhook_events is not None:
            updates["webhook_events"] = request.webhook_events
        
        if request.is_active is not None:
            updates["is_active"] = request.is_active
        
        endpoint = await data_export_service.update_integration_endpoint(
            endpoint_id=endpoint_id,
            tenant_id=tenant_id,
            updates=updates
        )
        
        if not endpoint:
            raise HTTPException(status_code=404, detail="Integration endpoint not found")
        
        return {
            "success": True,
            "message": "Integration endpoint updated successfully",
            "integration_endpoint": {
                "id": endpoint.id,
                "name": endpoint.name,
                "endpoint_url": endpoint.endpoint_url,
                "auth_type": endpoint.auth_type,
                "data_types": [dt.value for dt in endpoint.data_types],
                "webhook_events": endpoint.webhook_events,
                "is_active": endpoint.is_active,
                "created_at": endpoint.created_at.isoformat(),
                "last_sync": endpoint.last_sync.isoformat() if endpoint.last_sync else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update integration endpoint", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update integration endpoint")


@router.delete("/integrations/{endpoint_id}")
async def delete_integration_endpoint(
    endpoint_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Delete an integration endpoint.
    
    Removes the integration endpoint configuration and stops
    any associated data synchronization processes.
    """
    try:
        success = await data_export_service.delete_integration_endpoint(
            endpoint_id=endpoint_id,
            tenant_id=tenant_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Integration endpoint not found")
        
        return {
            "success": True,
            "message": "Integration endpoint deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete integration endpoint", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete integration endpoint")


# Utility Endpoints

@router.get("/export/formats")
async def list_export_formats():
    """
    List available export formats.
    
    Returns all supported data export formats that can be used
    when creating export requests.
    """
    try:
        formats = [
            {
                "value": fmt.value,
                "name": fmt.value.upper(),
                "description": f"{fmt.value.upper()} format export"
            }
            for fmt in ExportFormat
        ]
        
        return {
            "success": True,
            "export_formats": formats
        }
        
    except Exception as e:
        logger.error("Failed to list export formats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list export formats")


@router.get("/export/data-types")
async def list_data_types():
    """
    List available data types for export.
    
    Returns all data types that can be exported from the system
    along with their descriptions.
    """
    try:
        data_types = [
            {
                "value": dt.value,
                "name": dt.value.replace("_", " ").title(),
                "description": f"{dt.value.replace('_', ' ').title()} data export"
            }
            for dt in DataType
        ]
        
        return {
            "success": True,
            "data_types": data_types
        }
        
    except Exception as e:
        logger.error("Failed to list data types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list data types")


@router.get("/integration/auth-types")
async def list_auth_types():
    """
    List available authentication types for integrations.
    
    Returns all supported authentication methods for
    external integration endpoints.
    """
    try:
        auth_types = [
            {
                "value": "api_key",
                "name": "API Key",
                "description": "API key authentication"
            },
            {
                "value": "bearer",
                "name": "Bearer Token",
                "description": "Bearer token authentication"
            },
            {
                "value": "basic",
                "name": "Basic Auth",
                "description": "Basic HTTP authentication"
            },
            {
                "value": "none",
                "name": "No Authentication",
                "description": "No authentication required"
            }
        ]
        
        return {
            "success": True,
            "auth_types": auth_types
        }
        
    except Exception as e:
        logger.error("Failed to list auth types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list auth types")


# API Documentation Endpoint

@router.get("/docs/api")
async def get_api_documentation():
    """
    Get comprehensive API documentation.
    
    Returns detailed documentation for all available API endpoints
    including request/response formats and authentication requirements.
    """
    try:
        documentation = {
            "api_version": "v1",
            "base_url": "/api/v1",
            "authentication": {
                "type": "Bearer Token",
                "description": "All API endpoints require authentication using a valid bearer token",
                "header": "Authorization: Bearer <token>"
            },
            "endpoints": {
                "data_export": {
                    "create_export": {
                        "method": "POST",
                        "path": "/export",
                        "description": "Create a new data export request",
                        "parameters": {
                            "data_type": "Type of data to export (calls, agents, analytics, etc.)",
                            "format": "Export format (json, csv, xml, xlsx)",
                            "filters": "Optional data filters",
                            "start_date": "Optional start date for data range",
                            "end_date": "Optional end date for data range"
                        }
                    },
                    "get_export_status": {
                        "method": "GET",
                        "path": "/export/{export_id}",
                        "description": "Get the status of a data export request"
                    },
                    "list_exports": {
                        "method": "GET",
                        "path": "/exports",
                        "description": "List all export requests for the tenant"
                    }
                },
                "integrations": {
                    "create_integration": {
                        "method": "POST",
                        "path": "/integrations",
                        "description": "Create a new external integration endpoint"
                    },
                    "get_integration": {
                        "method": "GET",
                        "path": "/integrations/{endpoint_id}",
                        "description": "Get details of a specific integration endpoint"
                    },
                    "list_integrations": {
                        "method": "GET",
                        "path": "/integrations",
                        "description": "List all integration endpoints for the tenant"
                    },
                    "update_integration": {
                        "method": "PUT",
                        "path": "/integrations/{endpoint_id}",
                        "description": "Update an existing integration endpoint"
                    },
                    "delete_integration": {
                        "method": "DELETE",
                        "path": "/integrations/{endpoint_id}",
                        "description": "Delete an integration endpoint"
                    }
                }
            },
            "rate_limits": {
                "export_requests": "10 requests per minute",
                "integration_management": "20 requests per minute",
                "data_retrieval": "100 requests per minute"
            },
            "supported_formats": [fmt.value for fmt in ExportFormat],
            "supported_data_types": [dt.value for dt in DataType]
        }
        
        return {
            "success": True,
            "documentation": documentation
        }
        
    except Exception as e:
        logger.error("Failed to get API documentation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get API documentation")