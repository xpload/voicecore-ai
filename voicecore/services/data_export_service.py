"""
Data Export Service for VoiceCore AI.

Implements data export in standard formats and external integration APIs
per Requirements 10.1 and 10.4.
"""

import uuid
import asyncio
import json
import csv
import io
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy import select, and_, func, desc, text
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import Call, Agent, Tenant
from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    XLSX = "xlsx"


class DataType(Enum):
    """Types of data that can be exported."""
    CALLS = "calls"
    AGENTS = "agents"
    ANALYTICS = "analytics"
    TRANSCRIPTS = "transcripts"
    VOICEMAILS = "voicemails"
    VIP_CALLERS = "vip_callers"
    CALLBACKS = "callbacks"
    EMOTIONS = "emotions"


@dataclass
class ExportRequest:
    """Data export request."""
    id: str
    tenant_id: uuid.UUID
    data_type: DataType
    format: ExportFormat
    filters: Dict[str, Any]
    date_range: Dict[str, datetime]
    status: str  # "pending", "processing", "completed", "failed"
    created_at: datetime
    completed_at: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class IntegrationEndpoint:
    """External integration endpoint configuration."""
    id: str
    tenant_id: uuid.UUID
    name: str
    endpoint_url: str
    auth_type: str  # "api_key", "bearer", "basic", "none"
    auth_credentials: Dict[str, str]
    data_types: List[DataType]
    webhook_events: List[str]
    is_active: bool
    created_at: datetime
    last_sync: Optional[datetime] = None


class DataExportService:
    """
    Comprehensive data export and integration service.
    
    Implements data export in standard formats and REST API
    for external integrations per Requirements 10.1 and 10.4.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Export requests storage
        self.export_requests: Dict[str, ExportRequest] = {}
        
        # Integration endpoints storage
        self.integration_endpoints: Dict[str, IntegrationEndpoint] = {}
        
        # Export processing queue
        self.export_queue: List[str] = []
        self.processing_exports = False
    
    async def create_export_request(
        self,
        tenant_id: uuid.UUID,
        data_type: DataType,
        format: ExportFormat,
        filters: Optional[Dict[str, Any]] = None,
        date_range: Optional[Dict[str, datetime]] = None
    ) -> ExportRequest:
        """
        Create a new data export request.
        
        Args:
            tenant_id: Tenant identifier
            data_type: Type of data to export
            format: Export format
            filters: Optional data filters
            date_range: Optional date range filter
            
        Returns:
            ExportRequest: Created export request
        """
        try:
            request_id = str(uuid.uuid4())
            
            # Set default date range if not provided
            if not date_range:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=30)
                date_range = {"start": start_date, "end": end_date}
            
            # Set default filters if not provided
            if not filters:
                filters = {}
            
            export_request = ExportRequest(
                id=request_id,
                tenant_id=tenant_id,
                data_type=data_type,
                format=format,
                filters=filters,
                date_range=date_range,
                status="pending",
                created_at=datetime.utcnow()
            )
            
            # Store export request
            self.export_requests[request_id] = export_request
            
            # Add to processing queue
            self.export_queue.append(request_id)
            
            self.logger.info(
                "Export request created",
                request_id=request_id,
                tenant_id=str(tenant_id),
                data_type=data_type.value,
                format=format.value
            )
            
            # Start processing if not already running
            if not self.processing_exports:
                asyncio.create_task(self._process_export_queue())
            
            return export_request
            
        except Exception as e:
            self.logger.error("Failed to create export request", error=str(e))
            raise
    
    async def get_export_request(
        self,
        request_id: str,
        tenant_id: uuid.UUID
    ) -> Optional[ExportRequest]:
        """
        Get export request by ID.
        
        Args:
            request_id: Export request ID
            tenant_id: Tenant identifier for access control
            
        Returns:
            ExportRequest or None if not found
        """
        try:
            if request_id not in self.export_requests:
                return None
            
            export_request = self.export_requests[request_id]
            
            # Verify tenant ownership
            if export_request.tenant_id != tenant_id:
                return None
            
            return export_request
            
        except Exception as e:
            self.logger.error("Failed to get export request", error=str(e))
            return None
    
    async def list_export_requests(
        self,
        tenant_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExportRequest]:
        """
        List export requests for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of requests to return
            offset: Number of requests to skip
            
        Returns:
            List of export requests
        """
        try:
            tenant_requests = [
                req for req in self.export_requests.values()
                if req.tenant_id == tenant_id
            ]
            
            # Sort by creation date (newest first)
            tenant_requests.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply pagination
            return tenant_requests[offset:offset + limit]
            
        except Exception as e:
            self.logger.error("Failed to list export requests", error=str(e))
            return []
    
    async def _process_export_queue(self):
        """Process export requests in the queue."""
        self.processing_exports = True
        
        try:
            while self.export_queue:
                request_id = self.export_queue.pop(0)
                
                if request_id in self.export_requests:
                    await self._process_export_request(request_id)
                
                # Small delay between processing
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error("Error processing export queue", error=str(e))
        finally:
            self.processing_exports = False
    
    async def _process_export_request(self, request_id: str):
        """Process a single export request."""
        try:
            export_request = self.export_requests[request_id]
            export_request.status = "processing"
            
            self.logger.info(
                "Processing export request",
                request_id=request_id,
                data_type=export_request.data_type.value
            )
            
            # Extract data based on type
            data = await self._extract_data(export_request)
            
            # Convert to requested format
            exported_data = await self._format_data(data, export_request.format)
            
            # Store exported data (in production, save to file system or cloud storage)
            file_path = f"/tmp/export_{request_id}.{export_request.format.value}"
            file_size = len(exported_data.encode('utf-8'))
            
            # Update request status
            export_request.status = "completed"
            export_request.completed_at = datetime.utcnow()
            export_request.file_path = file_path
            export_request.file_size = file_size
            
            self.logger.info(
                "Export request completed",
                request_id=request_id,
                file_size=file_size
            )
            
        except Exception as e:
            # Update request with error
            export_request.status = "failed"
            export_request.error_message = str(e)
            export_request.completed_at = datetime.utcnow()
            
            self.logger.error(
                "Export request failed",
                request_id=request_id,
                error=str(e)
            )
    
    async def _extract_data(self, export_request: ExportRequest) -> List[Dict[str, Any]]:
        """Extract data based on export request."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, export_request.tenant_id)
                
                if export_request.data_type == DataType.CALLS:
                    return await self._extract_calls_data(session, export_request)
                elif export_request.data_type == DataType.AGENTS:
                    return await self._extract_agents_data(session, export_request)
                elif export_request.data_type == DataType.ANALYTICS:
                    return await self._extract_analytics_data(session, export_request)
                elif export_request.data_type == DataType.TRANSCRIPTS:
                    return await self._extract_transcripts_data(session, export_request)
                else:
                    # For other data types, return empty list for now
                    return []
                    
        except Exception as e:
            self.logger.error("Failed to extract data", error=str(e))
            raise
    
    async def _extract_calls_data(self, session, export_request: ExportRequest) -> List[Dict[str, Any]]:
        """Extract calls data."""
        try:
            query = select(Call).where(
                and_(
                    Call.tenant_id == export_request.tenant_id,
                    Call.created_at >= export_request.date_range["start"],
                    Call.created_at <= export_request.date_range["end"]
                )
            ).options(selectinload(Call.agent))
            
            # Apply filters
            if "status" in export_request.filters:
                query = query.where(Call.status == export_request.filters["status"])
            
            if "agent_id" in export_request.filters:
                query = query.where(Call.agent_id == export_request.filters["agent_id"])
            
            result = await session.execute(query)
            calls = result.scalars().all()
            
            return [
                {
                    "id": str(call.id),
                    "phone_number": call.phone_number,
                    "caller_name": call.caller_name,
                    "status": call.status,
                    "duration": call.duration,
                    "agent_name": call.agent.name if call.agent else None,
                    "created_at": call.created_at.isoformat(),
                    "ended_at": call.ended_at.isoformat() if call.ended_at else None,
                    "call_type": call.call_type,
                    "is_spam": call.is_spam,
                    "transcript": call.transcript
                }
                for call in calls
            ]
            
        except Exception as e:
            self.logger.error("Failed to extract calls data", error=str(e))
            raise
    
    async def _extract_agents_data(self, session, export_request: ExportRequest) -> List[Dict[str, Any]]:
        """Extract agents data."""
        try:
            query = select(Agent).where(Agent.tenant_id == export_request.tenant_id)
            
            # Apply filters
            if "department" in export_request.filters:
                query = query.where(Agent.department == export_request.filters["department"])
            
            if "status" in export_request.filters:
                query = query.where(Agent.status == export_request.filters["status"])
            
            result = await session.execute(query)
            agents = result.scalars().all()
            
            return [
                {
                    "id": str(agent.id),
                    "name": agent.name,
                    "email": agent.email,
                    "extension": agent.extension,
                    "department": agent.department,
                    "status": agent.status,
                    "is_available": agent.is_available,
                    "created_at": agent.created_at.isoformat(),
                    "last_activity": agent.last_activity.isoformat() if agent.last_activity else None
                }
                for agent in agents
            ]
            
        except Exception as e:
            self.logger.error("Failed to extract agents data", error=str(e))
            raise
    
    async def _extract_analytics_data(self, session, export_request: ExportRequest) -> List[Dict[str, Any]]:
        """Extract analytics data."""
        try:
            # Get call statistics
            call_stats_query = select(
                func.count(Call.id).label("total_calls"),
                func.avg(Call.duration).label("avg_duration"),
                func.sum(func.case((Call.is_spam == True, 1), else_=0)).label("spam_calls"),
                func.date(Call.created_at).label("date")
            ).where(
                and_(
                    Call.tenant_id == export_request.tenant_id,
                    Call.created_at >= export_request.date_range["start"],
                    Call.created_at <= export_request.date_range["end"]
                )
            ).group_by(func.date(Call.created_at))
            
            result = await session.execute(call_stats_query)
            stats = result.all()
            
            return [
                {
                    "date": stat.date.isoformat(),
                    "total_calls": stat.total_calls,
                    "average_duration": float(stat.avg_duration) if stat.avg_duration else 0,
                    "spam_calls": stat.spam_calls
                }
                for stat in stats
            ]
            
        except Exception as e:
            self.logger.error("Failed to extract analytics data", error=str(e))
            raise
    
    async def _extract_transcripts_data(self, session, export_request: ExportRequest) -> List[Dict[str, Any]]:
        """Extract transcripts data."""
        try:
            query = select(Call).where(
                and_(
                    Call.tenant_id == export_request.tenant_id,
                    Call.transcript.isnot(None),
                    Call.created_at >= export_request.date_range["start"],
                    Call.created_at <= export_request.date_range["end"]
                )
            )
            
            result = await session.execute(query)
            calls = result.scalars().all()
            
            return [
                {
                    "call_id": str(call.id),
                    "phone_number": call.phone_number,
                    "transcript": call.transcript,
                    "duration": call.duration,
                    "created_at": call.created_at.isoformat()
                }
                for call in calls if call.transcript
            ]
            
        except Exception as e:
            self.logger.error("Failed to extract transcripts data", error=str(e))
            raise
    
    async def _format_data(self, data: List[Dict[str, Any]], format: ExportFormat) -> str:
        """Format data in the requested format."""
        try:
            if format == ExportFormat.JSON:
                return json.dumps(data, indent=2, default=str)
            
            elif format == ExportFormat.CSV:
                if not data:
                    return ""
                
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                return output.getvalue()
            
            elif format == ExportFormat.XML:
                # Simple XML format
                xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<data>']
                
                for item in data:
                    xml_lines.append('  <record>')
                    for key, value in item.items():
                        xml_lines.append(f'    <{key}>{value}</{key}>')
                    xml_lines.append('  </record>')
                
                xml_lines.append('</data>')
                return '\n'.join(xml_lines)
            
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            self.logger.error("Failed to format data", error=str(e))
            raise
    
    # Integration Endpoints Management
    
    async def create_integration_endpoint(
        self,
        tenant_id: uuid.UUID,
        name: str,
        endpoint_url: str,
        auth_type: str,
        auth_credentials: Dict[str, str],
        data_types: List[DataType],
        webhook_events: Optional[List[str]] = None
    ) -> IntegrationEndpoint:
        """Create a new integration endpoint."""
        try:
            endpoint_id = str(uuid.uuid4())
            
            if not webhook_events:
                webhook_events = []
            
            endpoint = IntegrationEndpoint(
                id=endpoint_id,
                tenant_id=tenant_id,
                name=name,
                endpoint_url=endpoint_url,
                auth_type=auth_type,
                auth_credentials=auth_credentials,
                data_types=data_types,
                webhook_events=webhook_events,
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            self.integration_endpoints[endpoint_id] = endpoint
            
            self.logger.info(
                "Integration endpoint created",
                endpoint_id=endpoint_id,
                tenant_id=str(tenant_id),
                name=name
            )
            
            return endpoint
            
        except Exception as e:
            self.logger.error("Failed to create integration endpoint", error=str(e))
            raise
    
    async def get_integration_endpoint(
        self,
        endpoint_id: str,
        tenant_id: uuid.UUID
    ) -> Optional[IntegrationEndpoint]:
        """Get integration endpoint by ID."""
        try:
            if endpoint_id not in self.integration_endpoints:
                return None
            
            endpoint = self.integration_endpoints[endpoint_id]
            
            # Verify tenant ownership
            if endpoint.tenant_id != tenant_id:
                return None
            
            return endpoint
            
        except Exception as e:
            self.logger.error("Failed to get integration endpoint", error=str(e))
            return None
    
    async def list_integration_endpoints(
        self,
        tenant_id: uuid.UUID
    ) -> List[IntegrationEndpoint]:
        """List integration endpoints for a tenant."""
        try:
            return [
                endpoint for endpoint in self.integration_endpoints.values()
                if endpoint.tenant_id == tenant_id
            ]
            
        except Exception as e:
            self.logger.error("Failed to list integration endpoints", error=str(e))
            return []
    
    async def update_integration_endpoint(
        self,
        endpoint_id: str,
        tenant_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> Optional[IntegrationEndpoint]:
        """Update integration endpoint."""
        try:
            endpoint = await self.get_integration_endpoint(endpoint_id, tenant_id)
            if not endpoint:
                return None
            
            # Update allowed fields
            allowed_fields = {
                "name", "endpoint_url", "auth_type", "auth_credentials",
                "data_types", "webhook_events", "is_active"
            }
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(endpoint, field, value)
            
            self.logger.info(
                "Integration endpoint updated",
                endpoint_id=endpoint_id,
                tenant_id=str(tenant_id)
            )
            
            return endpoint
            
        except Exception as e:
            self.logger.error("Failed to update integration endpoint", error=str(e))
            return None
    
    async def delete_integration_endpoint(
        self,
        endpoint_id: str,
        tenant_id: uuid.UUID
    ) -> bool:
        """Delete integration endpoint."""
        try:
            endpoint = await self.get_integration_endpoint(endpoint_id, tenant_id)
            if not endpoint:
                return False
            
            del self.integration_endpoints[endpoint_id]
            
            self.logger.info(
                "Integration endpoint deleted",
                endpoint_id=endpoint_id,
                tenant_id=str(tenant_id)
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete integration endpoint", error=str(e))
            return False


# Global service instance
data_export_service = DataExportService()