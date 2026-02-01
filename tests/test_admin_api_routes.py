"""
Unit tests for admin API routes in VoiceCore AI.

Tests API endpoints for both Super Admin and Tenant Admin panels,
including authentication, request/response handling, and error cases.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from voicecore.main import app
from voicecore.services.admin_service import (
    AdminService, SystemMetrics, AdminServiceError, UnauthorizedAdminError
)
from voicecore.services.tenant_admin_service import (
    TenantAdminService, TenantAnalytics, UnauthorizedTenantAdminError
)


class TestSuperAdminAPIRoutes:
    """Test cases for Super Admin API routes."""
    
    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)
    
    @pytest.fixture
    def valid_super_admin_headers(self):
        """Valid super admin headers for API requests."""
        return {
            "X-Admin-User-ID": "super_admin",
            "X-Admin-API-Key": "test_super_admin_key"
        }
    
    @pytest.fixture
    def invalid_super_admin_headers(self):
        """Invalid super admin headers for API requests."""
        return {
            "X-Admin-User-ID": "invalid_user",
            "X-Admin-API-Key": "invalid_key"
        }
    
    def test_get_system_metrics_success(self, client):
        """Test successful system metrics API endpoint."""
        with patch('voicecore.api.admin_routes.verify_super_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = mock_admin_service
            
            # Mock system metrics
            mock_metrics = SystemMetrics(
                total_tenants=10,
                active_tenants=8,
                total_agents=50,
                active_agents=45,
                total_calls_today=200,
                total_calls_this_month=5000,
                average_call_duration=150.5,
                system_uptime_hours=720.0,
                storage_usage_gb=25.5,
                api_requests_per_minute=100.0,
                error_rate_percentage=0.1
            )
            mock_admin_service.get_system_metrics.return_value = mock_metrics
            
            response = client.get("/api/v1/admin/metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_tenants"] == 10
            assert data["active_tenants"] == 8
            assert data["total_agents"] == 50
            assert data["average_call_duration"] == 150.5
    
    def test_get_system_metrics_unauthorized(self, client, invalid_super_admin_headers):
        """Test system metrics endpoint with unauthorized access."""
        response = client.get("/api/v1/admin/metrics", headers=invalid_super_admin_headers)
        assert response.status_code == 422  # Missing required headers or validation error
    
    def test_get_system_metrics_service_error(self, client):
        """Test system metrics endpoint with service error."""
        with patch('voicecore.api.admin_routes.verify_super_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = mock_admin_service
            mock_admin_service.get_system_metrics.side_effect = AdminServiceError("Database error")
            
            response = client.get("/api/v1/admin/metrics")
            
            assert response.status_code == 400
            assert "Database error" in response.json()["detail"]
    
    def test_get_all_tenants_success(self, client):
        """Test successful get all tenants API endpoint."""
        with patch('voicecore.api.admin_routes.verify_super_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = mock_admin_service
            
            # Mock tenant summaries
            mock_tenant_summaries = [
                MagicMock(
                    to_dict=lambda: {
                        "tenant_id": str(uuid.uuid4()),
                        "company_name": "Test Company 1",
                        "status": "active",
                        "created_at": datetime.utcnow().isoformat(),
                        "last_activity": datetime.utcnow().isoformat(),
                        "total_agents": 10,
                        "active_agents": 8,
                        "calls_this_month": 500,
                        "storage_usage_mb": 1024.0,
                        "monthly_cost_cents": 5000
                    }
                ),
                MagicMock(
                    to_dict=lambda: {
                        "tenant_id": str(uuid.uuid4()),
                        "company_name": "Test Company 2",
                        "status": "active",
                        "created_at": datetime.utcnow().isoformat(),
                        "last_activity": None,
                        "total_agents": 5,
                        "active_agents": 5,
                        "calls_this_month": 200,
                        "storage_usage_mb": 512.0,
                        "monthly_cost_cents": 2000
                    }
                )
            ]
            mock_admin_service.get_all_tenants_summary.return_value = mock_tenant_summaries
            
            response = client.get("/api/v1/admin/tenants?limit=10&offset=0")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["company_name"] == "Test Company 1"
            assert data[1]["company_name"] == "Test Company 2"
    
    def test_create_tenant_as_admin_success(self, client):
        """Test successful tenant creation by super admin."""
        with patch('voicecore.api.admin_routes.verify_super_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = mock_admin_service
            
            tenant_data = {
                "tenant_id": str(uuid.uuid4()),
                "company_name": "New Test Company",
                "status": "active"
            }
            mock_admin_service.create_tenant_as_admin.return_value = tenant_data
            
            request_data = {
                "company_name": "New Test Company",
                "admin_email": "admin@newtest.com",
                "phone_number": "+1234567890"
            }
            
            response = client.post("/api/v1/admin/tenants", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "tenant_data" in data
    
    def test_suspend_tenant_success(self, client):
        """Test successful tenant suspension."""
        with patch('voicecore.api.admin_routes.verify_super_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = mock_admin_service
            mock_admin_service.suspend_tenant.return_value = True
            
            tenant_id = str(uuid.uuid4())
            request_data = {"reason": "Policy violation"}
            
            response = client.post(f"/api/v1/admin/tenants/{tenant_id}/suspend", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert tenant_id in data["message"]
    
    def test_update_system_configuration_success(self, client):
        """Test successful system configuration update."""
        with patch('voicecore.api.admin_routes.verify_super_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = mock_admin_service
            
            # Mock updated configuration
            from voicecore.services.admin_service import SystemConfiguration
            updated_config = SystemConfiguration(
                max_tenants=2000,
                max_agents_per_tenant=150,
                default_call_timeout_seconds=300,
                max_recording_duration_minutes=60,
                auto_transcription_enabled=False,
                spam_detection_enabled=True,
                rate_limit_requests_per_minute=1500,
                maintenance_mode=True,
                debug_logging_enabled=False
            )
            mock_admin_service.update_system_configuration.return_value = updated_config
            
            request_data = {
                "max_tenants": 2000,
                "auto_transcription_enabled": False,
                "maintenance_mode": True
            }
            
            response = client.put("/api/v1/admin/configuration", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["max_tenants"] == 2000
            assert data["auto_transcription_enabled"] is False
            assert data["maintenance_mode"] is True
    
    def test_get_admin_panel_status_no_auth(self, client):
        """Test admin panel status endpoint (no authentication required)."""
        response = client.get("/api/v1/admin/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["service"] == "VoiceCore AI Super Admin Panel"
        assert data["authentication_required"] is True


class TestTenantAdminAPIRoutes:
    """Test cases for Tenant Admin API routes."""
    
    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_tenant_id(self):
        """Sample tenant ID for testing."""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def valid_tenant_admin_headers(self, sample_tenant_id):
        """Valid tenant admin headers for API requests."""
        return {
            "X-Tenant-Admin-User-ID": "tenant_admin",
            "X-Tenant-Admin-API-Key": f"tenant_{sample_tenant_id}_admin_key"
        }
    
    def test_get_tenant_analytics_success(self, client, sample_tenant_id):
        """Test successful tenant analytics API endpoint."""
        with patch('voicecore.api.tenant_admin_routes.verify_tenant_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = (mock_admin_service, uuid.UUID(sample_tenant_id))
            
            # Mock tenant analytics
            mock_analytics = TenantAnalytics(
                tenant_id=uuid.UUID(sample_tenant_id),
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow(),
                total_calls=100,
                answered_calls=85,
                missed_calls=15,
                average_call_duration=120.5,
                total_call_duration=10242,
                peak_call_hour=14,
                busiest_day="Tuesday",
                agent_utilization=75.0,
                ai_resolution_rate=80.0,
                transfer_rate=15.0,
                spam_calls_blocked=5,
                top_call_sources=[{"source": "Direct", "count": 60}],
                department_performance=[{"department": "Sales", "calls": 40}]
            )
            mock_admin_service.get_tenant_analytics.return_value = mock_analytics
            
            response = client.get(f"/api/v1/tenant-admin/{sample_tenant_id}/analytics?period_days=30")
            
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == sample_tenant_id
            assert data["total_calls"] == 100
            assert data["answered_calls"] == 85
            assert data["peak_call_hour"] == 14
            assert data["busiest_day"] == "Tuesday"
    
    def test_get_tenant_analytics_unauthorized(self, client, sample_tenant_id):
        """Test tenant analytics endpoint with unauthorized access."""
        # Missing headers
        response = client.get(f"/api/v1/tenant-admin/{sample_tenant_id}/analytics")
        assert response.status_code == 422  # Missing required headers
    
    def test_update_ai_configuration_success(self, client, sample_tenant_id):
        """Test successful AI configuration update."""
        with patch('voicecore.api.tenant_admin_routes.verify_tenant_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = (mock_admin_service, uuid.UUID(sample_tenant_id))
            mock_admin_service.update_ai_configuration.return_value = True
            
            request_data = {
                "ai_name": "Sofia",
                "ai_personality": "Friendly and professional",
                "training_mode": True
            }
            
            response = client.put(
                f"/api/v1/tenant-admin/{sample_tenant_id}/ai-configuration",
                json=request_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "updated_fields" in data
    
    def test_create_knowledge_base_entry_success(self, client, sample_tenant_id):
        """Test successful knowledge base entry creation."""
        with patch('voicecore.api.tenant_admin_routes.verify_tenant_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = (mock_admin_service, uuid.UUID(sample_tenant_id))
            
            created_entry = {
                "id": str(uuid.uuid4()),
                "question": "What are your hours?",
                "answer": "We are open 9-5 Monday to Friday",
                "category": "general",
                "is_approved": False,
                "created_at": datetime.utcnow().isoformat()
            }
            mock_admin_service.create_knowledge_base_entry.return_value = created_entry
            
            request_data = {
                "question": "What are your hours?",
                "answer": "We are open 9-5 Monday to Friday",
                "category": "general"
            }
            
            response = client.post(
                f"/api/v1/tenant-admin/{sample_tenant_id}/knowledge-base/entries",
                json=request_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "entry" in data
            assert data["entry"]["question"] == request_data["question"]
    
    def test_update_knowledge_base_entry_success(self, client, sample_tenant_id):
        """Test successful knowledge base entry update."""
        with patch('voicecore.api.tenant_admin_routes.verify_tenant_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = (mock_admin_service, uuid.UUID(sample_tenant_id))
            mock_admin_service.update_knowledge_base_entry.return_value = True
            
            entry_id = str(uuid.uuid4())
            request_data = {
                "answer": "Updated answer: We are open 8-6 Monday to Friday",
                "is_approved": True
            }
            
            response = client.put(
                f"/api/v1/tenant-admin/{sample_tenant_id}/knowledge-base/entries/{entry_id}",
                json=request_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "updated_fields" in data
    
    def test_update_knowledge_base_entry_not_found(self, client, sample_tenant_id):
        """Test knowledge base entry update when entry not found."""
        with patch('voicecore.api.tenant_admin_routes.verify_tenant_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = (mock_admin_service, uuid.UUID(sample_tenant_id))
            mock_admin_service.update_knowledge_base_entry.return_value = False
            
            entry_id = str(uuid.uuid4())
            request_data = {"answer": "Updated answer"}
            
            response = client.put(
                f"/api/v1/tenant-admin/{sample_tenant_id}/knowledge-base/entries/{entry_id}",
                json=request_data
            )
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
    
    def test_delete_knowledge_base_entry_success(self, client, sample_tenant_id):
        """Test successful knowledge base entry deletion."""
        with patch('voicecore.api.tenant_admin_routes.verify_tenant_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = (mock_admin_service, uuid.UUID(sample_tenant_id))
            mock_admin_service.delete_knowledge_base_entry.return_value = True
            
            entry_id = str(uuid.uuid4())
            
            response = client.delete(
                f"/api/v1/tenant-admin/{sample_tenant_id}/knowledge-base/entries/{entry_id}"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "deleted successfully" in data["message"]
    
    def test_get_tenant_configuration_success(self, client, sample_tenant_id):
        """Test successful tenant configuration retrieval."""
        with patch('voicecore.api.tenant_admin_routes.verify_tenant_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = (mock_admin_service, uuid.UUID(sample_tenant_id))
            
            mock_configuration = {
                "tenant": {
                    "id": sample_tenant_id,
                    "name": "Test Tenant",
                    "is_active": True
                },
                "ai_settings": {
                    "ai_name": "Sofia",
                    "ai_personality": "Professional and friendly"
                },
                "departments": [
                    {"name": "Customer Service", "is_active": True}
                ],
                "spam_rules": [
                    {"name": "Insurance Block", "is_active": True}
                ]
            }
            mock_admin_service.get_tenant_configuration.return_value = mock_configuration
            
            response = client.get(f"/api/v1/tenant-admin/{sample_tenant_id}/configuration")
            
            assert response.status_code == 200
            data = response.json()
            assert data["tenant"]["id"] == sample_tenant_id
            assert data["ai_settings"]["ai_name"] == "Sofia"
            assert len(data["departments"]) == 1
            assert len(data["spam_rules"]) == 1
    
    def test_update_tenant_configuration_success(self, client, sample_tenant_id):
        """Test successful tenant configuration update."""
        with patch('voicecore.api.tenant_admin_routes.verify_tenant_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = (mock_admin_service, uuid.UUID(sample_tenant_id))
            mock_admin_service.update_tenant_configuration.return_value = True
            
            request_data = {
                "tenant": {
                    "name": "Updated Tenant Name",
                    "contact_email": "new@email.com"
                },
                "ai_settings": {
                    "ai_name": "Alex",
                    "welcome_message": "Welcome to our updated service"
                }
            }
            
            response = client.put(
                f"/api/v1/tenant-admin/{sample_tenant_id}/configuration",
                json=request_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "updated_sections" in data
    
    def test_get_tenant_admin_panel_status_no_auth(self, client, sample_tenant_id):
        """Test tenant admin panel status endpoint (no authentication required)."""
        response = client.get(f"/api/v1/tenant-admin/{sample_tenant_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["service"] == "VoiceCore AI Tenant Admin Panel"
        assert data["tenant_id"] == sample_tenant_id
        assert data["authentication_required"] is True
        assert "features" in data


class TestAdminAPIErrorHandling:
    """Test cases for admin API error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)
    
    def test_super_admin_authentication_failure(self, client):
        """Test super admin authentication failure handling."""
        with patch('voicecore.api.admin_routes.verify_super_admin') as mock_verify:
            mock_verify.side_effect = UnauthorizedAdminError("Invalid credentials")
            
            response = client.get("/api/v1/admin/metrics")
            
            assert response.status_code == 403
            assert "Invalid credentials" in response.json()["detail"]
    
    def test_tenant_admin_authentication_failure(self, client):
        """Test tenant admin authentication failure handling."""
        tenant_id = str(uuid.uuid4())
        
        with patch('voicecore.api.tenant_admin_routes.verify_tenant_admin') as mock_verify:
            mock_verify.side_effect = UnauthorizedTenantAdminError("Invalid tenant credentials")
            
            response = client.get(f"/api/v1/tenant-admin/{tenant_id}/analytics")
            
            assert response.status_code == 403
            assert "Invalid tenant credentials" in response.json()["detail"]
    
    def test_invalid_request_data_validation(self, client):
        """Test API validation for invalid request data."""
        # Test super admin tenant creation with missing required fields
        response = client.post("/api/v1/admin/tenants", json={})
        assert response.status_code == 422  # Validation error
        
        # Test tenant admin AI config update with invalid data types
        tenant_id = str(uuid.uuid4())
        invalid_data = {
            "max_transfer_attempts": "not_a_number"  # Should be int
        }
        response = client.put(
            f"/api/v1/tenant-admin/{tenant_id}/ai-configuration",
            json=invalid_data
        )
        assert response.status_code == 422  # Validation error
    
    def test_internal_server_error_handling(self, client):
        """Test internal server error handling."""
        with patch('voicecore.api.admin_routes.verify_super_admin') as mock_verify:
            mock_admin_service = MagicMock()
            mock_verify.return_value = mock_admin_service
            mock_admin_service.get_system_metrics.side_effect = Exception("Unexpected error")
            
            response = client.get("/api/v1/admin/metrics")
            
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]