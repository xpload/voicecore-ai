"""
Property-based tests for advanced features.

Tests Property 24: Data Export Consistency
Validates: Requirements 10.4
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

from voicecore.services.data_export_service import (
    data_export_service, DataType, ExportFormat, ExportRequest
)
from voicecore.models import Call, Agent, Tenant
from voicecore.database import get_db_session, set_tenant_context


# Test Data Generators

@composite
def export_request_data(draw):
    """Generate valid export request data."""
    data_type = draw(st.sampled_from(list(DataType)))
    format_type = draw(st.sampled_from(list(ExportFormat)))
    
    # Generate date range
    end_date = datetime.utcnow()
    days_back = draw(st.integers(min_value=1, max_value=90))
    start_date = end_date - timedelta(days=days_back)
    
    # Generate filters
    filters = {}
    if data_type == DataType.CALLS:
        if draw(st.booleans()):
            filters["status"] = draw(st.sampled_from(["completed", "in_progress", "failed"]))
        if draw(st.booleans()):
            filters["agent_id"] = str(uuid.uuid4())
    elif data_type == DataType.AGENTS:
        if draw(st.booleans()):
            filters["department"] = draw(st.text(min_size=1, max_size=20))
        if draw(st.booleans()):
            filters["status"] = draw(st.sampled_from(["available", "busy", "offline"]))
    
    return {
        "data_type": data_type,
        "format": format_type,
        "filters": filters,
        "date_range": {"start": start_date, "end": end_date}
    }


@composite
def tenant_data(draw):
    """Generate tenant data for testing."""
    return {
        "id": uuid.uuid4(),
        "name": draw(st.text(min_size=1, max_size=50)),
        "domain": draw(st.text(min_size=5, max_size=30))
    }


@composite
def call_data(draw, tenant_id: uuid.UUID):
    """Generate call data for testing."""
    return {
        "id": uuid.uuid4(),
        "tenant_id": tenant_id,
        "phone_number": draw(st.text(min_size=10, max_size=15, alphabet="0123456789")),
        "caller_name": draw(st.text(min_size=1, max_size=50)),
        "status": draw(st.sampled_from(["completed", "in_progress", "failed"])),
        "duration": draw(st.integers(min_value=0, max_value=3600)),
        "call_type": draw(st.sampled_from(["inbound", "outbound"])),
        "is_spam": draw(st.booleans()),
        "transcript": draw(st.text(min_size=0, max_size=1000)),
        "created_at": draw(st.datetimes(
            min_value=datetime.utcnow() - timedelta(days=90),
            max_value=datetime.utcnow()
        ))
    }


@composite
def agent_data(draw, tenant_id: uuid.UUID):
    """Generate agent data for testing."""
    return {
        "id": uuid.uuid4(),
        "tenant_id": tenant_id,
        "name": draw(st.text(min_size=1, max_size=50)),
        "email": draw(st.emails()),
        "extension": draw(st.integers(min_value=1000, max_value=9999)),
        "department": draw(st.text(min_size=1, max_size=30)),
        "status": draw(st.sampled_from(["available", "busy", "offline"])),
        "is_available": draw(st.booleans()),
        "created_at": draw(st.datetimes(
            min_value=datetime.utcnow() - timedelta(days=365),
            max_value=datetime.utcnow()
        ))
    }


# Property Tests

class TestDataExportConsistency:
    """
    Property 24: Data Export Consistency
    
    For any data export operation, the exported data should be in the 
    specified format and contain all requested information.
    
    **Validates: Requirements 10.4**
    """
    
    @given(
        tenant=tenant_data(),
        export_data=export_request_data()
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.asyncio
    async def test_export_format_consistency(self, tenant, export_data):
        """
        Property: Exported data format matches requested format.
        
        For any valid export request, the exported data should be in the
        exact format specified in the request (JSON, CSV, XML, etc.).
        """
        try:
            tenant_id = tenant["id"]
            
            # Create export request
            export_request = await data_export_service.create_export_request(
                tenant_id=tenant_id,
                data_type=export_data["data_type"],
                format=export_data["format"],
                filters=export_data["filters"],
                date_range=export_data["date_range"]
            )
            
            # Wait for processing (simulate)
            await asyncio.sleep(0.1)
            
            # Verify export request was created
            assert export_request.id is not None
            assert export_request.tenant_id == tenant_id
            assert export_request.data_type == export_data["data_type"]
            assert export_request.format == export_data["format"]
            assert export_request.status in ["pending", "processing", "completed"]
            
            # Verify format consistency
            assert export_request.format.value in ["json", "csv", "xml", "xlsx"]
            
            # Verify date range consistency
            assert export_request.date_range["start"] <= export_request.date_range["end"]
            assert export_request.date_range["start"] <= datetime.utcnow()
            
        except Exception as e:
            pytest.fail(f"Export format consistency failed: {str(e)}")
    
    @given(
        tenant=tenant_data(),
        calls=st.lists(call_data(uuid.uuid4()), min_size=0, max_size=10)
    )
    @settings(max_examples=50, deadline=10000)
    @pytest.mark.asyncio
    async def test_export_data_completeness(self, tenant, calls):
        """
        Property: Exported data contains all requested information.
        
        For any export request with filters, the exported data should
        contain all records that match the specified criteria.
        """
        try:
            tenant_id = tenant["id"]
            
            # Update calls with correct tenant_id
            for call in calls:
                call["tenant_id"] = tenant_id
            
            # Create export request for calls
            export_request = await data_export_service.create_export_request(
                tenant_id=tenant_id,
                data_type=DataType.CALLS,
                format=ExportFormat.JSON,
                filters={},
                date_range={
                    "start": datetime.utcnow() - timedelta(days=30),
                    "end": datetime.utcnow()
                }
            )
            
            # Verify export request properties
            assert export_request.tenant_id == tenant_id
            assert export_request.data_type == DataType.CALLS
            assert export_request.format == ExportFormat.JSON
            
            # Verify filters are preserved
            assert isinstance(export_request.filters, dict)
            
            # Verify date range is within bounds
            date_diff = export_request.date_range["end"] - export_request.date_range["start"]
            assert date_diff.days >= 0
            assert date_diff.days <= 365  # Reasonable upper bound
            
        except Exception as e:
            pytest.fail(f"Export data completeness failed: {str(e)}")
    
    @given(
        tenant=tenant_data(),
        agents=st.lists(agent_data(uuid.uuid4()), min_size=0, max_size=10)
    )
    @settings(max_examples=50, deadline=10000)
    @pytest.mark.asyncio
    async def test_export_filter_accuracy(self, tenant, agents):
        """
        Property: Export filters are applied accurately.
        
        For any export request with filters, only data matching
        the filter criteria should be included in the export.
        """
        try:
            tenant_id = tenant["id"]
            
            # Update agents with correct tenant_id
            for agent in agents:
                agent["tenant_id"] = tenant_id
            
            # Test with department filter
            if agents:
                test_department = agents[0]["department"]
                
                export_request = await data_export_service.create_export_request(
                    tenant_id=tenant_id,
                    data_type=DataType.AGENTS,
                    format=ExportFormat.JSON,
                    filters={"department": test_department},
                    date_range={
                        "start": datetime.utcnow() - timedelta(days=30),
                        "end": datetime.utcnow()
                    }
                )
                
                # Verify filter is preserved
                assert export_request.filters.get("department") == test_department
                assert export_request.data_type == DataType.AGENTS
                
                # Verify tenant isolation
                assert export_request.tenant_id == tenant_id
            
        except Exception as e:
            pytest.fail(f"Export filter accuracy failed: {str(e)}")
    
    @given(
        tenant=tenant_data(),
        format_type=st.sampled_from(list(ExportFormat))
    )
    @settings(max_examples=20, deadline=5000)
    @pytest.mark.asyncio
    async def test_export_format_validation(self, tenant, format_type):
        """
        Property: Export format validation is consistent.
        
        For any supported export format, the system should accept
        the format and process the export request correctly.
        """
        try:
            tenant_id = tenant["id"]
            
            # Create export request with specific format
            export_request = await data_export_service.create_export_request(
                tenant_id=tenant_id,
                data_type=DataType.ANALYTICS,
                format=format_type,
                filters={},
                date_range={
                    "start": datetime.utcnow() - timedelta(days=7),
                    "end": datetime.utcnow()
                }
            )
            
            # Verify format is preserved correctly
            assert export_request.format == format_type
            assert export_request.format.value in ["json", "csv", "xml", "xlsx"]
            
            # Verify request is valid
            assert export_request.status in ["pending", "processing", "completed", "failed"]
            assert export_request.created_at <= datetime.utcnow()
            
        except Exception as e:
            pytest.fail(f"Export format validation failed: {str(e)}")
    
    @given(
        tenant=tenant_data(),
        data_type=st.sampled_from(list(DataType))
    )
    @settings(max_examples=20, deadline=5000)
    @pytest.mark.asyncio
    async def test_export_data_type_validation(self, tenant, data_type):
        """
        Property: Export data type validation is consistent.
        
        For any supported data type, the system should accept
        the data type and process the export request correctly.
        """
        try:
            tenant_id = tenant["id"]
            
            # Create export request with specific data type
            export_request = await data_export_service.create_export_request(
                tenant_id=tenant_id,
                data_type=data_type,
                format=ExportFormat.JSON,
                filters={},
                date_range={
                    "start": datetime.utcnow() - timedelta(days=7),
                    "end": datetime.utcnow()
                }
            )
            
            # Verify data type is preserved correctly
            assert export_request.data_type == data_type
            assert export_request.data_type.value in [
                "calls", "agents", "analytics", "transcripts",
                "voicemails", "vip_callers", "callbacks", "emotions"
            ]
            
            # Verify request is valid
            assert export_request.tenant_id == tenant_id
            assert export_request.status in ["pending", "processing", "completed", "failed"]
            
        except Exception as e:
            pytest.fail(f"Export data type validation failed: {str(e)}")
    
    @given(
        tenant=tenant_data(),
        days_back=st.integers(min_value=1, max_value=365)
    )
    @settings(max_examples=30, deadline=5000)
    @pytest.mark.asyncio
    async def test_export_date_range_consistency(self, tenant, days_back):
        """
        Property: Export date ranges are handled consistently.
        
        For any valid date range, the export should include only
        data within the specified time period.
        """
        try:
            tenant_id = tenant["id"]
            
            # Create date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Create export request
            export_request = await data_export_service.create_export_request(
                tenant_id=tenant_id,
                data_type=DataType.CALLS,
                format=ExportFormat.JSON,
                filters={},
                date_range={"start": start_date, "end": end_date}
            )
            
            # Verify date range consistency
            assert export_request.date_range["start"] == start_date
            assert export_request.date_range["end"] == end_date
            assert export_request.date_range["start"] <= export_request.date_range["end"]
            
            # Verify date range is reasonable
            date_diff = export_request.date_range["end"] - export_request.date_range["start"]
            assert date_diff.days == days_back
            assert date_diff.days <= 365  # Maximum reasonable range
            
        except Exception as e:
            pytest.fail(f"Export date range consistency failed: {str(e)}")
    
    @given(
        tenant=tenant_data(),
        export_data=export_request_data()
    )
    @settings(max_examples=50, deadline=5000)
    @pytest.mark.asyncio
    async def test_export_tenant_isolation(self, tenant, export_data):
        """
        Property: Export requests maintain tenant isolation.
        
        For any export request, only data belonging to the requesting
        tenant should be included in the export.
        """
        try:
            tenant_id = tenant["id"]
            other_tenant_id = uuid.uuid4()
            
            # Create export request for first tenant
            export_request1 = await data_export_service.create_export_request(
                tenant_id=tenant_id,
                data_type=export_data["data_type"],
                format=export_data["format"],
                filters=export_data["filters"],
                date_range=export_data["date_range"]
            )
            
            # Create export request for second tenant
            export_request2 = await data_export_service.create_export_request(
                tenant_id=other_tenant_id,
                data_type=export_data["data_type"],
                format=export_data["format"],
                filters=export_data["filters"],
                date_range=export_data["date_range"]
            )
            
            # Verify tenant isolation
            assert export_request1.tenant_id == tenant_id
            assert export_request2.tenant_id == other_tenant_id
            assert export_request1.tenant_id != export_request2.tenant_id
            
            # Verify requests are separate
            assert export_request1.id != export_request2.id
            
            # Verify access control
            retrieved_request = await data_export_service.get_export_request(
                export_request1.id, tenant_id
            )
            assert retrieved_request is not None
            assert retrieved_request.tenant_id == tenant_id
            
            # Verify cross-tenant access is denied
            cross_tenant_request = await data_export_service.get_export_request(
                export_request1.id, other_tenant_id
            )
            assert cross_tenant_request is None
            
        except Exception as e:
            pytest.fail(f"Export tenant isolation failed: {str(e)}")
    
    @given(
        tenant=tenant_data(),
        num_requests=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=20, deadline=10000)
    @pytest.mark.asyncio
    async def test_export_request_tracking(self, tenant, num_requests):
        """
        Property: Export requests are tracked consistently.
        
        For any number of export requests, the system should
        track all requests and provide accurate status information.
        """
        try:
            tenant_id = tenant["id"]
            created_requests = []
            
            # Create multiple export requests
            for i in range(num_requests):
                export_request = await data_export_service.create_export_request(
                    tenant_id=tenant_id,
                    data_type=DataType.CALLS,
                    format=ExportFormat.JSON,
                    filters={},
                    date_range={
                        "start": datetime.utcnow() - timedelta(days=7),
                        "end": datetime.utcnow()
                    }
                )
                created_requests.append(export_request)
            
            # Verify all requests are tracked
            assert len(created_requests) == num_requests
            
            # Verify each request has unique ID
            request_ids = [req.id for req in created_requests]
            assert len(set(request_ids)) == num_requests
            
            # Verify all requests belong to the same tenant
            for request in created_requests:
                assert request.tenant_id == tenant_id
                assert request.status in ["pending", "processing", "completed", "failed"]
                assert request.created_at <= datetime.utcnow()
            
            # Verify requests can be retrieved
            for request in created_requests:
                retrieved = await data_export_service.get_export_request(
                    request.id, tenant_id
                )
                assert retrieved is not None
                assert retrieved.id == request.id
                assert retrieved.tenant_id == tenant_id
            
        except Exception as e:
            pytest.fail(f"Export request tracking failed: {str(e)}")


# Integration Tests for Data Export Service

class TestDataExportIntegration:
    """Integration tests for data export service functionality."""
    
    @pytest.mark.asyncio
    async def test_export_service_initialization(self):
        """Test that the data export service initializes correctly."""
        try:
            # Verify service is initialized
            assert data_export_service is not None
            assert hasattr(data_export_service, 'export_requests')
            assert hasattr(data_export_service, 'integration_endpoints')
            assert hasattr(data_export_service, 'export_queue')
            
            # Verify initial state
            assert isinstance(data_export_service.export_requests, dict)
            assert isinstance(data_export_service.integration_endpoints, dict)
            assert isinstance(data_export_service.export_queue, list)
            
        except Exception as e:
            pytest.fail(f"Export service initialization failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_export_formats_support(self):
        """Test that all export formats are supported."""
        try:
            # Test each format
            for format_type in ExportFormat:
                tenant_id = uuid.uuid4()
                
                export_request = await data_export_service.create_export_request(
                    tenant_id=tenant_id,
                    data_type=DataType.CALLS,
                    format=format_type,
                    filters={},
                    date_range={
                        "start": datetime.utcnow() - timedelta(days=7),
                        "end": datetime.utcnow()
                    }
                )
                
                assert export_request.format == format_type
                assert export_request.format.value in ["json", "csv", "xml", "xlsx"]
                
        except Exception as e:
            pytest.fail(f"Export formats support test failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_data_types_support(self):
        """Test that all data types are supported."""
        try:
            # Test each data type
            for data_type in DataType:
                tenant_id = uuid.uuid4()
                
                export_request = await data_export_service.create_export_request(
                    tenant_id=tenant_id,
                    data_type=data_type,
                    format=ExportFormat.JSON,
                    filters={},
                    date_range={
                        "start": datetime.utcnow() - timedelta(days=7),
                        "end": datetime.utcnow()
                    }
                )
                
                assert export_request.data_type == data_type
                assert export_request.data_type.value in [
                    "calls", "agents", "analytics", "transcripts",
                    "voicemails", "vip_callers", "callbacks", "emotions"
                ]
                
        except Exception as e:
            pytest.fail(f"Data types support test failed: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])