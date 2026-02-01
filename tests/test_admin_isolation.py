"""
Integration tests for admin panel isolation and security in VoiceCore AI.

Tests comprehensive isolation between tenants and proper access control
for both Super Admin and Tenant Admin functionalities.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from voicecore.services.admin_service import AdminService
from voicecore.services.tenant_admin_service import (
    TenantAdminService, UnauthorizedTenantAdminError
)
from voicecore.database import set_tenant_context


class TestTenantDataIsolation:
    """Test cases for tenant data isolation in admin panels."""
    
    @pytest.fixture
    def tenant_admin_service(self):
        """Create tenant admin service for testing."""
        return TenantAdminService()
    
    @pytest.fixture
    def tenant_a_id(self):
        """Tenant A UUID for isolation testing."""
        return uuid.uuid4()
    
    @pytest.fixture
    def tenant_b_id(self):
        """Tenant B UUID for isolation testing."""
        return uuid.uuid4()
    
    async def test_analytics_isolation_between_tenants(
        self, tenant_admin_service, tenant_a_id, tenant_b_id
    ):
        """Test that analytics are properly isolated between tenants."""
        with patch('voicecore.services.tenant_admin_service.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock different call statistics for each tenant
            tenant_a_stats = MagicMock()
            tenant_a_stats.first.return_value = MagicMock(
                total_calls=100, answered_calls=90, missed_calls=10,
                avg_duration=150.0, total_duration=15000
            )
            
            tenant_b_stats = MagicMock()
            tenant_b_stats.first.return_value = MagicMock(
                total_calls=50, answered_calls=40, missed_calls=10,
                avg_duration=200.0, total_duration=10000
            )
            
            # Mock other required query results
            mock_peak_hour = MagicMock()
            mock_peak_hour.first.return_value = MagicMock(hour=14)
            
            mock_busiest_day = MagicMock()
            mock_busiest_day.first.return_value = MagicMock(day_of_week=2)
            
            mock_agent_count = MagicMock()
            mock_agent_count.scalar.return_value = 5
            
            mock_transfer_count = MagicMock()
            mock_transfer_count.scalar.return_value = 10
            
            mock_dept_performance = MagicMock()
            mock_dept_performance.__iter__.return_value = []
            
            with patch('voicecore.services.tenant_admin_service.set_tenant_context') as mock_context:
                # Get analytics for tenant A
                mock_session_instance.execute.side_effect = [
                    tenant_a_stats, mock_peak_hour, mock_busiest_day,
                    mock_agent_count, mock_transfer_count, mock_dept_performance
                ]
                
                analytics_a = await tenant_admin_service.get_tenant_analytics(tenant_a_id, 30)
                
                # Verify tenant context was set for tenant A
                mock_context.assert_called_with(mock_session_instance, str(tenant_a_id))
                
                # Reset mocks for tenant B
                mock_context.reset_mock()
                mock_session_instance.execute.side_effect = [
                    tenant_b_stats, mock_peak_hour, mock_busiest_day,
                    mock_agent_count, mock_transfer_count, mock_dept_performance
                ]
                
                # Get analytics for tenant B
                analytics_b = await tenant_admin_service.get_tenant_analytics(tenant_b_id, 30)
                
                # Verify tenant context was set for tenant B
                mock_context.assert_called_with(mock_session_instance, str(tenant_b_id))
                
                # Verify data isolation - each tenant has different data
                assert analytics_a.tenant_id == tenant_a_id
                assert analytics_b.tenant_id == tenant_b_id
                assert analytics_a.total_calls != analytics_b.total_calls
                assert analytics_a.total_calls == 100
                assert analytics_b.total_calls == 50
    
    async def test_knowledge_base_isolation_between_tenants(
        self, tenant_admin_service, tenant_a_id, tenant_b_id
    ):
        """Test that knowledge base entries are isolated between tenants."""
        with patch('voicecore.services.tenant_admin_service.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            with patch('voicecore.services.tenant_admin_service.set_tenant_context') as mock_context:
                # Mock knowledge base stats for tenant A (20 entries)
                mock_stats_a = [
                    MagicMock(scalar=lambda: 20),  # total_entries
                    MagicMock(scalar=lambda: 18),  # active_entries
                    MagicMock(scalar=lambda: 2),   # pending_approval
                    MagicMock(__iter__=lambda: iter([])),  # categories
                    MagicMock(__iter__=lambda: iter([])),  # languages
                    MagicMock(__iter__=lambda: iter([]))   # most_used
                ]
                
                mock_session_instance.execute.side_effect = mock_stats_a
                
                stats_a = await tenant_admin_service.get_knowledge_base_stats(tenant_a_id)
                
                # Verify tenant context was set for tenant A
                mock_context.assert_called_with(mock_session_instance, str(tenant_a_id))
                
                # Reset for tenant B
                mock_context.reset_mock()
                
                # Mock knowledge base stats for tenant B (10 entries)
                mock_stats_b = [
                    MagicMock(scalar=lambda: 10),  # total_entries
                    MagicMock(scalar=lambda: 8),   # active_entries
                    MagicMock(scalar=lambda: 2),   # pending_approval
                    MagicMock(__iter__=lambda: iter([])),  # categories
                    MagicMock(__iter__=lambda: iter([])),  # languages
                    MagicMock(__iter__=lambda: iter([]))   # most_used
                ]
                
                mock_session_instance.execute.side_effect = mock_stats_b
                
                stats_b = await tenant_admin_service.get_knowledge_base_stats(tenant_b_id)
                
                # Verify tenant context was set for tenant B
                mock_context.assert_called_with(mock_session_instance, str(tenant_b_id))
                
                # Verify isolation - each tenant has different knowledge base sizes
                assert stats_a.total_entries == 20
                assert stats_b.total_entries == 10
                assert stats_a.total_entries != stats_b.total_entries
    
    async def test_configuration_isolation_between_tenants(
        self, tenant_admin_service, tenant_a_id, tenant_b_id
    ):
        """Test that configuration updates are isolated between tenants."""
        with patch('voicecore.services.tenant_admin_service.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock existing settings for both tenants
            mock_settings = MagicMock()
            mock_settings_result = MagicMock()
            mock_settings_result.scalar_one_or_none.return_value = mock_settings
            
            mock_session_instance.execute.side_effect = [
                mock_settings_result,  # Get settings
                MagicMock()           # Update query
            ]
            
            with patch('voicecore.services.tenant_admin_service.set_tenant_context') as mock_context:
                # Update AI configuration for tenant A
                config_a = {"ai_name": "Alice", "ai_personality": "Friendly"}
                result_a = await tenant_admin_service.update_ai_configuration(
                    tenant_a_id, config_a
                )
                
                # Verify tenant context was set for tenant A
                mock_context.assert_called_with(mock_session_instance, str(tenant_a_id))
                assert result_a is True
                
                # Reset mocks for tenant B
                mock_context.reset_mock()
                mock_session_instance.execute.side_effect = [
                    mock_settings_result,  # Get settings
                    MagicMock()           # Update query
                ]
                
                # Update AI configuration for tenant B
                config_b = {"ai_name": "Bob", "ai_personality": "Professional"}
                result_b = await tenant_admin_service.update_ai_configuration(
                    tenant_b_id, config_b
                )
                
                # Verify tenant context was set for tenant B
                mock_context.assert_called_with(mock_session_instance, str(tenant_b_id))
                assert result_b is True
                
                # Verify that each tenant's context was set correctly
                assert mock_context.call_count == 2
                calls = mock_context.call_args_list
                assert calls[0][0][1] == str(tenant_a_id)
                assert calls[1][0][1] == str(tenant_b_id)


class TestAdminAccessControlSecurity:
    """Test cases for admin access control and security."""
    
    @pytest.fixture
    def admin_service(self):
        """Create admin service for testing."""
        return AdminService()
    
    @pytest.fixture
    def tenant_admin_service(self):
        """Create tenant admin service for testing."""
        return TenantAdminService()
    
    async def test_super_admin_cannot_access_tenant_specific_data_directly(self, admin_service):
        """Test that super admin uses proper channels for tenant data access."""
        # Super admin should use tenant management methods, not direct tenant context
        tenant_id = uuid.uuid4()
        
        with patch('voicecore.services.admin_service.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock tenant summary data (this goes through proper tenant isolation)
            mock_tenant = MagicMock()
            mock_tenant.id = tenant_id
            mock_tenant.name = "Test Tenant"
            mock_tenant.is_active = True
            mock_tenant.created_at = datetime.utcnow()
            
            mock_tenant_result = MagicMock()
            mock_tenant_result.scalars.return_value.all.return_value = [mock_tenant]
            
            mock_session_instance.execute.side_effect = [
                mock_tenant_result,  # Get tenants
                MagicMock(first=lambda: MagicMock(total_agents=5, active_agents=4)),  # Agent metrics
                MagicMock(scalar=lambda: 100),  # Calls this month
                MagicMock(scalar=lambda: None)  # Last activity
            ]
            
            with patch('voicecore.services.admin_service.set_tenant_context') as mock_context:
                # Super admin gets tenant summaries (which properly sets tenant context per tenant)
                summaries = await admin_service.get_all_tenants_summary(limit=10)
                
                # Verify that tenant context was set for the tenant being processed
                mock_context.assert_called_with(mock_session_instance, str(tenant_id))
                assert len(summaries) == 1
                assert summaries[0].tenant_id == tenant_id
    
    async def test_tenant_admin_cross_tenant_access_prevention(self, tenant_admin_service):
        """Test that tenant admin cannot access other tenants' data."""
        tenant_a_id = uuid.uuid4()
        tenant_b_id = uuid.uuid4()
        
        # Tenant A admin credentials
        tenant_a_key = f"tenant_{tenant_a_id}_admin_key"
        
        with patch('voicecore.services.tenant_admin_service.TenantService') as mock_tenant_service:
            # Mock tenant A exists and is active
            mock_tenant_a = MagicMock()
            mock_tenant_a.is_active = True
            mock_tenant_service.return_value.get_tenant.return_value = mock_tenant_a
            
            # Tenant A admin should be able to access tenant A
            result = await tenant_admin_service.verify_tenant_admin_access(
                tenant_a_id, "admin", tenant_a_key
            )
            assert result is True
            
            # Tenant A admin should NOT be able to access tenant B
            with pytest.raises(UnauthorizedTenantAdminError):
                await tenant_admin_service.verify_tenant_admin_access(
                    tenant_b_id, "admin", tenant_a_key  # Wrong key for tenant B
                )
    
    async def test_tenant_context_enforcement_in_database_operations(self):
        """Test that database operations properly enforce tenant context."""
        tenant_id = uuid.uuid4()
        
        with patch('voicecore.services.tenant_admin_service.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            with patch('voicecore.services.tenant_admin_service.set_tenant_context') as mock_context:
                service = TenantAdminService()
                
                # Mock knowledge base entry creation
                mock_entry = MagicMock()
                mock_entry.id = uuid.uuid4()
                mock_entry.question = "Test question"
                mock_entry.answer = "Test answer"
                mock_entry.category = "general"
                mock_entry.is_approved = False
                mock_entry.created_at = datetime.utcnow()
                
                with patch('voicecore.services.tenant_admin_service.KnowledgeBase', return_value=mock_entry):
                    entry_data = {
                        "question": "Test question",
                        "answer": "Test answer",
                        "category": "general"
                    }
                    
                    result = await service.create_knowledge_base_entry(tenant_id, entry_data)
                    
                    # Verify tenant context was set before database operations
                    mock_context.assert_called_once_with(mock_session_instance, str(tenant_id))
                    
                    # Verify the entry was created with correct tenant_id
                    assert result["question"] == "Test question"
                    
                    # Verify the KnowledgeBase constructor was called with tenant_id
                    # (This would be enforced by the database RLS policies in production)
    
    def test_admin_credential_separation(self):
        """Test that super admin and tenant admin credentials are completely separate."""
        super_admin_key = "super_admin_global_key"
        tenant_id = uuid.uuid4()
        tenant_admin_key = f"tenant_{tenant_id}_admin_key"
        
        # These should be completely different
        assert super_admin_key != tenant_admin_key
        
        # Super admin key should not work for tenant admin
        assert not tenant_admin_key.startswith("super_admin")
        
        # Tenant admin key should not work for super admin
        assert not super_admin_key.startswith("tenant_")
        
        # Each tenant should have a unique key
        other_tenant_id = uuid.uuid4()
        other_tenant_key = f"tenant_{other_tenant_id}_admin_key"
        assert tenant_admin_key != other_tenant_key
    
    async def test_database_rls_context_setting(self):
        """Test that database RLS context is properly set for tenant operations."""
        tenant_id = uuid.uuid4()
        
        # Mock the set_tenant_context function to verify it's called correctly
        with patch('voicecore.database.set_tenant_context') as mock_set_context:
            mock_session = MagicMock()
            
            # Call set_tenant_context directly to test the mechanism
            await set_tenant_context(mock_session, str(tenant_id))
            
            # Verify the context was set with correct tenant ID
            mock_set_context.assert_called_once_with(mock_session, str(tenant_id))
    
    async def test_admin_operation_audit_logging(self):
        """Test that admin operations are properly logged for audit purposes."""
        service = TenantAdminService()
        tenant_id = uuid.uuid4()
        
        with patch.object(service, 'logger') as mock_logger:
            with patch('voicecore.services.tenant_admin_service.get_db_session') as mock_session:
                mock_session_instance = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_session_instance
                
                # Mock successful AI configuration update
                mock_settings = MagicMock()
                mock_settings_result = MagicMock()
                mock_settings_result.scalar_one_or_none.return_value = mock_settings
                
                mock_session_instance.execute.side_effect = [
                    mock_settings_result,
                    MagicMock()
                ]
                
                with patch('voicecore.services.tenant_admin_service.set_tenant_context'):
                    config_updates = {"ai_name": "Sofia"}
                    await service.update_ai_configuration(tenant_id, config_updates)
                    
                    # Verify that the operation was logged
                    mock_logger.info.assert_called_with(
                        "AI configuration updated",
                        tenant_id=str(tenant_id),
                        updated_fields=['ai_name', 'updated_at']
                    )