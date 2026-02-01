"""
Property-based tests for VoiceCore AI correctness properties.

These tests validate universal properties that should hold across
all valid executions of the system using property-based testing.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, date
from typing import List, Dict, Any
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

# Test framework setup
from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    Tenant, TenantSettings, Agent, Department, Call, 
    KnowledgeBase, SpamRule, CallAnalytics
)
from voicecore.services.tenant_service import TenantService
from voicecore.utils.security import SecurityUtils


# Custom strategies for generating test data
@composite
def tenant_data(draw):
    """Generate valid tenant data for testing."""
    return {
        "name": draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs')))),
        "subdomain": draw(st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Nd')))),
        "contact_email": draw(st.emails()),
        "plan_type": draw(st.sampled_from(["basic", "professional", "enterprise"])),
        "monthly_credit_limit": draw(st.integers(min_value=100, max_value=10000)),
        "is_active": draw(st.booleans())
    }


@composite
def agent_data(draw, tenant_id: str):
    """Generate valid agent data for testing."""
    return {
        "tenant_id": tenant_id,
        "email": draw(st.emails()),
        "name": draw(st.text(min_size=2, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')))),
        "first_name": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        "last_name": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        "extension": draw(st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Nd')))),
        "is_active": draw(st.booleans()),
        "is_manager": draw(st.booleans())
    }


@composite
def call_data(draw, tenant_id: str):
    """Generate valid call data for testing."""
    return {
        "tenant_id": tenant_id,
        "twilio_call_sid": f"CA{draw(st.text(min_size=32, max_size=32, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'))))}",
        "from_number": f"+1{draw(st.text(min_size=10, max_size=10, alphabet=st.characters(whitelist_categories=('Nd'))))}",
        "to_number": f"+1{draw(st.text(min_size=10, max_size=10, alphabet=st.characters(whitelist_categories=('Nd'))))}",
        "direction": draw(st.sampled_from(["inbound", "outbound"])),
        "status": draw(st.sampled_from(["initiated", "ringing", "in_progress", "completed", "failed"])),
        "duration": draw(st.integers(min_value=0, max_value=3600)),
        "spam_score": draw(st.floats(min_value=0.0, max_value=1.0))
    }


class TestTenantDataIsolation:
    """
    Property 1: Tenant Data Isolation
    
    For any two different tenants in the system, data operations for one tenant 
    should never return or modify data belonging to the other tenant.
    
    Validates: Requirements 1.1, 1.3
    """
    
    @pytest.mark.asyncio
    @given(
        tenant1_data=tenant_data(),
        tenant2_data=tenant_data()
    )
    @settings(max_examples=50, deadline=30000)
    async def test_tenant_data_isolation_property(self, tenant1_data, tenant2_data):
        """
        **Property 1: Tenant Data Isolation**
        **Validates: Requirements 1.1, 1.3**
        
        Test that data operations for one tenant never return or modify 
        data belonging to another tenant.
        """
        # Ensure tenants have different subdomains
        assume(tenant1_data["subdomain"] != tenant2_data["subdomain"])
        assume(tenant1_data["contact_email"] != tenant2_data["contact_email"])
        
        tenant_service = TenantService()
        
        try:
            # Create two separate tenants
            tenant1 = await tenant_service.create_tenant(tenant1_data)
            tenant2 = await tenant_service.create_tenant(tenant2_data)
            
            # Create test data for each tenant
            async with get_db_session() as session:
                # Set context for tenant1 and create agent
                await set_tenant_context(session, str(tenant1.id))
                
                agent1_data = {
                    "tenant_id": tenant1.id,
                    "email": "agent1@test.com",
                    "name": "Agent One",
                    "first_name": "Agent",
                    "last_name": "One",
                    "extension": "101",
                    "department_id": None,  # Will be set after creating department
                    "is_active": True,
                    "is_manager": False,
                    "status": "not_available",
                    "max_concurrent_calls": 1,
                    "skills": ["customer_service"],
                    "languages": ["en"]
                }
                
                # Create department for tenant1
                dept1 = Department(
                    tenant_id=tenant1.id,
                    name="Customer Service",
                    code="CS",
                    is_active=True,
                    is_default=True,
                    max_queue_size=10,
                    queue_timeout=300,
                    priority=1,
                    routing_strategy="round_robin"
                )
                session.add(dept1)
                await session.flush()
                
                agent1_data["department_id"] = dept1.id
                agent1 = Agent(**agent1_data)
                session.add(agent1)
                await session.flush()
                
                # Set context for tenant2 and create agent
                await set_tenant_context(session, str(tenant2.id))
                
                # Create department for tenant2
                dept2 = Department(
                    tenant_id=tenant2.id,
                    name="Customer Service",
                    code="CS",
                    is_active=True,
                    is_default=True,
                    max_queue_size=10,
                    queue_timeout=300,
                    priority=1,
                    routing_strategy="round_robin"
                )
                session.add(dept2)
                await session.flush()
                
                agent2_data = {
                    "tenant_id": tenant2.id,
                    "email": "agent2@test.com",
                    "name": "Agent Two",
                    "first_name": "Agent",
                    "last_name": "Two",
                    "extension": "102",
                    "department_id": dept2.id,
                    "is_active": True,
                    "is_manager": False,
                    "status": "not_available",
                    "max_concurrent_calls": 1,
                    "skills": ["customer_service"],
                    "languages": ["en"]
                }
                
                agent2 = Agent(**agent2_data)
                session.add(agent2)
                await session.commit()
                
                # Test isolation: Query agents from tenant1 context
                await set_tenant_context(session, str(tenant1.id))
                result1 = await session.execute(
                    "SELECT id, name FROM agents WHERE tenant_id = current_setting('app.current_tenant')::UUID"
                )
                tenant1_agents = result1.fetchall()
                
                # Test isolation: Query agents from tenant2 context
                await set_tenant_context(session, str(tenant2.id))
                result2 = await session.execute(
                    "SELECT id, name FROM agents WHERE tenant_id = current_setting('app.current_tenant')::UUID"
                )
                tenant2_agents = result2.fetchall()
                
                # Verify isolation: Each tenant should only see their own data
                assert len(tenant1_agents) == 1, "Tenant1 should see exactly 1 agent"
                assert len(tenant2_agents) == 1, "Tenant2 should see exactly 1 agent"
                
                # Verify no cross-tenant data leakage
                tenant1_agent_ids = {str(agent[0]) for agent in tenant1_agents}
                tenant2_agent_ids = {str(agent[0]) for agent in tenant2_agents}
                
                assert tenant1_agent_ids.isdisjoint(tenant2_agent_ids), \
                    "Tenant data should be completely isolated - no shared agent IDs"
                
                # Test update isolation: Update agent in tenant1 context
                await set_tenant_context(session, str(tenant1.id))
                await session.execute(
                    "UPDATE agents SET name = 'Updated Agent One' WHERE id = :agent_id",
                    {"agent_id": agent1.id}
                )
                await session.commit()
                
                # Verify tenant2 data unchanged
                await set_tenant_context(session, str(tenant2.id))
                result3 = await session.execute(
                    "SELECT name FROM agents WHERE id = :agent_id",
                    {"agent_id": agent2.id}
                )
                unchanged_name = result3.scalar()
                assert unchanged_name == "Agent Two", "Tenant2 data should remain unchanged"
                
        except Exception as e:
            pytest.fail(f"Tenant data isolation property failed: {str(e)}")
        
        finally:
            # Cleanup: Delete test tenants
            try:
                await tenant_service.delete_tenant(tenant1.id)
                await tenant_service.delete_tenant(tenant2.id)
            except:
                pass  # Ignore cleanup errors


class TestTenantProvisioning:
    """
    Property 2: Tenant Provisioning Completeness
    
    For any newly created tenant, the system should provision all required 
    isolated resources including configuration, database schemas, and default settings.
    
    Validates: Requirements 1.2
    """
    
    @pytest.mark.asyncio
    @given(tenant_data=tenant_data())
    @settings(max_examples=30, deadline=20000)
    async def test_tenant_provisioning_completeness_property(self, tenant_data):
        """
        **Property 2: Tenant Provisioning Completeness**
        **Validates: Requirements 1.2**
        
        Test that newly created tenants have all required resources provisioned.
        """
        tenant_service = TenantService()
        
        try:
            # Create tenant
            tenant = await tenant_service.create_tenant(tenant_data)
            
            # Verify tenant was created with all required fields
            assert tenant.id is not None, "Tenant should have an ID"
            assert tenant.name == tenant_data["name"], "Tenant name should match input"
            assert tenant.subdomain == tenant_data["subdomain"], "Tenant subdomain should match input"
            assert tenant.contact_email == tenant_data["contact_email"], "Tenant email should match input"
            assert tenant.is_active == tenant_data["is_active"], "Tenant status should match input"
            assert tenant.monthly_credit_limit == tenant_data["monthly_credit_limit"], "Credit limit should match input"
            assert tenant.current_usage == 0, "New tenant should start with zero usage"
            assert tenant.settings is not None, "Tenant should have settings object"
            assert tenant.created_at is not None, "Tenant should have creation timestamp"
            assert tenant.updated_at is not None, "Tenant should have update timestamp"
            
            # Verify tenant can be retrieved
            retrieved_tenant = await tenant_service.get_tenant(tenant.id)
            assert retrieved_tenant is not None, "Tenant should be retrievable after creation"
            assert retrieved_tenant.id == tenant.id, "Retrieved tenant should match created tenant"
            
            # Verify tenant context can be set
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant.id))
                
                # Verify context was set correctly
                result = await session.execute(
                    "SELECT current_setting('app.current_tenant', true)"
                )
                current_tenant = result.scalar()
                assert current_tenant == str(tenant.id), "Tenant context should be set correctly"
            
        except Exception as e:
            pytest.fail(f"Tenant provisioning completeness property failed: {str(e)}")
        
        finally:
            # Cleanup
            try:
                await tenant_service.delete_tenant(tenant.id)
            except:
                pass


class TestTenantDataCleanup:
    """
    Property 3: Tenant Data Cleanup
    
    For any deleted tenant, all associated data should be completely removed 
    from the system within the specified time limit.
    
    Validates: Requirements 1.4
    """
    
    @pytest.mark.asyncio
    @given(tenant_data=tenant_data())
    @settings(max_examples=20, deadline=25000)
    async def test_tenant_data_cleanup_property(self, tenant_data):
        """
        **Property 3: Tenant Data Cleanup**
        **Validates: Requirements 1.4**
        
        Test that deleted tenants have all associated data completely removed.
        """
        tenant_service = TenantService()
        
        try:
            # Create tenant
            tenant = await tenant_service.create_tenant(tenant_data)
            tenant_id = tenant.id
            
            # Create associated data
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Create department
                department = Department(
                    tenant_id=tenant_id,
                    name="Test Department",
                    code="TEST",
                    is_active=True,
                    is_default=True,
                    max_queue_size=10,
                    queue_timeout=300,
                    priority=1,
                    routing_strategy="round_robin"
                )
                session.add(department)
                await session.flush()
                
                # Create agent
                agent = Agent(
                    tenant_id=tenant_id,
                    email="test@example.com",
                    name="Test Agent",
                    first_name="Test",
                    last_name="Agent",
                    extension="999",
                    department_id=department.id,
                    is_active=True,
                    is_manager=False,
                    status="not_available",
                    max_concurrent_calls=1,
                    skills=["test"],
                    languages=["en"]
                )
                session.add(agent)
                
                # Create knowledge base entry
                knowledge = KnowledgeBase(
                    tenant_id=tenant_id,
                    question="Test question?",
                    answer="Test answer",
                    category="general",
                    priority=1,
                    confidence_threshold=0.8,
                    is_active=True,
                    is_approved=True,
                    language="en"
                )
                session.add(knowledge)
                await session.commit()
                
                # Verify data exists before deletion
                dept_count = await session.execute(
                    "SELECT COUNT(*) FROM departments WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                assert dept_count.scalar() == 1, "Department should exist before deletion"
                
                agent_count = await session.execute(
                    "SELECT COUNT(*) FROM agents WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                assert agent_count.scalar() == 1, "Agent should exist before deletion"
                
                kb_count = await session.execute(
                    "SELECT COUNT(*) FROM knowledge_base WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                assert kb_count.scalar() == 1, "Knowledge base entry should exist before deletion"
            
            # Delete tenant
            await tenant_service.delete_tenant(tenant_id)
            
            # Verify all associated data is deleted
            async with get_db_session() as session:
                # Check tenant is deleted
                tenant_exists = await session.execute(
                    "SELECT COUNT(*) FROM tenants WHERE id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                assert tenant_exists.scalar() == 0, "Tenant should be completely deleted"
                
                # Check associated data is deleted (CASCADE should handle this)
                dept_count = await session.execute(
                    "SELECT COUNT(*) FROM departments WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                assert dept_count.scalar() == 0, "All departments should be deleted"
                
                agent_count = await session.execute(
                    "SELECT COUNT(*) FROM agents WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                assert agent_count.scalar() == 0, "All agents should be deleted"
                
                kb_count = await session.execute(
                    "SELECT COUNT(*) FROM knowledge_base WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                assert kb_count.scalar() == 0, "All knowledge base entries should be deleted"
                
        except Exception as e:
            pytest.fail(f"Tenant data cleanup property failed: {str(e)}")


class TestPrivacyCompliance:
    """
    Property 12: Privacy Compliance
    
    For any data storage or logging operation, the system should never store 
    IP addresses, geolocation, or location data of agents.
    
    Validates: Requirements 5.1, 5.5
    """
    
    @given(
        data_with_sensitive_info=st.dictionaries(
            keys=st.sampled_from([
                "user_data", "client_ip", "remote_addr", "geolocation", 
                "latitude", "longitude", "location", "coordinates",
                "ip_address", "x_forwarded_for", "real_ip"
            ]),
            values=st.one_of(
                st.text(min_size=1, max_size=50),
                st.floats(min_value=-180, max_value=180),
                st.integers(min_value=0, max_value=255)
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=5000)
    def test_privacy_compliance_property(self, data_with_sensitive_info):
        """
        **Property 12: Privacy Compliance**
        **Validates: Requirements 5.1, 5.5**
        
        Test that sensitive data is never stored in logs or database.
        """
        # Test data sanitization
        sanitized_data = SecurityUtils.sanitize_data(data_with_sensitive_info)
        
        # Verify no IP addresses are present in sanitized data
        sensitive_patterns = [
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',  # IPv4
            r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',  # IPv6
            r'\b-?\d{1,3}\.\d+,\s*-?\d{1,3}\.\d+\b'  # Coordinates
        ]
        
        sanitized_str = str(sanitized_data)
        
        for pattern in sensitive_patterns:
            import re
            matches = re.findall(pattern, sanitized_str)
            assert len(matches) == 0, f"Sanitized data should not contain pattern: {pattern}"
        
        # Verify sensitive keys are redacted
        sensitive_keys = [
            'client_ip', 'remote_addr', 'geolocation', 'latitude', 
            'longitude', 'location', 'coordinates', 'ip_address'
        ]
        
        for key in sensitive_keys:
            if key in data_with_sensitive_info:
                if isinstance(sanitized_data.get(key), str):
                    assert "REDACTED" in sanitized_data[key], f"Sensitive key {key} should be redacted"


class TestDataEncryption:
    """
    Property 13: Data Encryption
    
    For any data transmission or storage operation, the data should be encrypted 
    using approved encryption standards.
    
    Validates: Requirements 5.3
    """
    
    @given(sensitive_data=st.text(min_size=1, max_size=1000))
    @settings(max_examples=50, deadline=10000)
    def test_data_encryption_property(self, sensitive_data):
        """
        **Property 13: Data Encryption**
        **Validates: Requirements 5.3**
        
        Test that sensitive data is properly encrypted and decrypted.
        """
        # Test encryption
        encrypted_data = SecurityUtils.encrypt_sensitive_data(sensitive_data)
        
        # Verify data is actually encrypted (different from original)
        assert encrypted_data != sensitive_data, "Encrypted data should differ from original"
        assert len(encrypted_data) > 0, "Encrypted data should not be empty"
        assert sensitive_data not in encrypted_data, "Original data should not appear in encrypted form"
        
        # Test decryption
        decrypted_data = SecurityUtils.decrypt_sensitive_data(encrypted_data)
        
        # Verify decryption works correctly
        assert decrypted_data == sensitive_data, "Decrypted data should match original"
        
        # Test that different data produces different encrypted results
        if len(sensitive_data) > 1:
            different_data = sensitive_data[:-1] + ("x" if sensitive_data[-1] != "x" else "y")
            different_encrypted = SecurityUtils.encrypt_sensitive_data(different_data)
            assert different_encrypted != encrypted_data, "Different data should produce different encrypted results"


if __name__ == "__main__":
    # Run property tests with verbose output
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-x",  # Stop on first failure
        "--hypothesis-show-statistics"
    ])


# Additional property tests for comprehensive tenant operations coverage

class TestTenantOperationsProperties:
    """Additional property tests for tenant operations."""
    
    @pytest.mark.asyncio
    @given(
        tenant_data=tenant_data(),
        update_data=st.dictionaries(
            keys=st.sampled_from(["name", "monthly_credit_limit", "is_active"]),
            values=st.one_of(
                st.text(min_size=1, max_size=100),
                st.integers(min_value=100, max_value=10000),
                st.booleans()
            ),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=30, deadline=20000)
    async def test_tenant_update_preserves_isolation_property(self, tenant_data, update_data):
        """
        Test that tenant updates preserve data isolation between tenants.
        
        This property ensures that updating one tenant never affects another tenant's data.
        """
        tenant_service = TenantService()
        
        try:
            # Create two tenants
            tenant1_data = tenant_data.copy()
            tenant2_data = tenant_data.copy()
            tenant2_data["subdomain"] = f"{tenant_data.get('subdomain', 'test')}2"
            tenant2_data["contact_email"] = f"2{tenant_data['contact_email']}"
            
            tenant1 = await tenant_service.create_tenant(tenant1_data)
            tenant2 = await tenant_service.create_tenant(tenant2_data)
            
            # Get initial state of tenant2
            initial_tenant2 = await tenant_service.get_tenant(tenant2.id)
            
            # Update tenant1
            await tenant_service.update_tenant(tenant1.id, update_data)
            
            # Verify tenant2 is unchanged
            final_tenant2 = await tenant_service.get_tenant(tenant2.id)
            
            assert initial_tenant2.name == final_tenant2.name, "Tenant2 name should be unchanged"
            assert initial_tenant2.monthly_credit_limit == final_tenant2.monthly_credit_limit, "Tenant2 credit limit should be unchanged"
            assert initial_tenant2.is_active == final_tenant2.is_active, "Tenant2 status should be unchanged"
            assert initial_tenant2.updated_at == final_tenant2.updated_at, "Tenant2 update time should be unchanged"
            
        except Exception as e:
            pytest.fail(f"Tenant update isolation property failed: {str(e)}")
        
        finally:
            try:
                await tenant_service.delete_tenant(tenant1.id)
                await tenant_service.delete_tenant(tenant2.id)
            except:
                pass
    
    @pytest.mark.asyncio
    @given(tenant_data=tenant_data())
    @settings(max_examples=20, deadline=15000)
    async def test_tenant_settings_isolation_property(self, tenant_data):
        """
        Test that tenant settings are properly isolated between tenants.
        
        This property ensures that each tenant has independent settings that
        don't interfere with other tenants.
        """
        tenant_service = TenantService()
        
        try:
            # Create tenant
            tenant = await tenant_service.create_tenant(tenant_data)
            
            # Get tenant settings
            settings = await tenant_service.get_tenant_settings(tenant.id)
            
            assert settings is not None, "Tenant should have settings"
            assert settings.tenant_id == tenant.id, "Settings should belong to correct tenant"
            assert settings.ai_name is not None, "Settings should have AI name"
            assert settings.business_hours_start is not None, "Settings should have business hours"
            
            # Update settings
            new_settings = {
                "ai_name": "TestAI",
                "max_transfer_attempts": 5,
                "enable_spam_detection": False
            }
            
            updated_settings = await tenant_service.update_tenant_settings(tenant.id, new_settings)
            
            assert updated_settings is not None, "Settings should be updated"
            assert updated_settings.ai_name == "TestAI", "AI name should be updated"
            assert updated_settings.max_transfer_attempts == 5, "Transfer attempts should be updated"
            assert updated_settings.enable_spam_detection == False, "Spam detection should be updated"
            
        except Exception as e:
            pytest.fail(f"Tenant settings isolation property failed: {str(e)}")
        
        finally:
            try:
                await tenant_service.delete_tenant(tenant.id)
            except:
                pass
    
    @pytest.mark.asyncio
    @given(tenant_data=tenant_data())
    @settings(max_examples=15, deadline=20000)
    async def test_tenant_usage_stats_accuracy_property(self, tenant_data):
        """
        Test that tenant usage statistics are accurate and isolated.
        
        This property ensures that usage statistics reflect only the
        tenant's own data and are calculated correctly.
        """
        tenant_service = TenantService()
        
        try:
            # Create tenant
            tenant = await tenant_service.create_tenant(tenant_data)
            
            # Get initial usage stats
            stats = await tenant_service.get_tenant_usage_stats(tenant.id)
            
            assert stats is not None, "Tenant should have usage stats"
            assert "total_agents" in stats, "Stats should include agent count"
            assert "total_departments" in stats, "Stats should include department count"
            assert "current_usage" in stats, "Stats should include current usage"
            assert "monthly_credit_limit" in stats, "Stats should include credit limit"
            
            # Verify initial state
            assert stats["total_agents"] == 0, "New tenant should have 0 agents"
            assert stats["total_departments"] >= 2, "New tenant should have default departments"
            assert stats["current_usage"] == 0, "New tenant should have 0 usage"
            assert stats["monthly_credit_limit"] == tenant_data.get("monthly_credit_limit", 1000), "Credit limit should match"
            
            # Verify usage percentage calculation
            expected_percentage = (stats["current_usage"] / stats["monthly_credit_limit"]) * 100 if stats["monthly_credit_limit"] > 0 else 0
            assert abs(stats["usage_percentage"] - expected_percentage) < 0.01, "Usage percentage should be calculated correctly"
            
        except Exception as e:
            pytest.fail(f"Tenant usage stats accuracy property failed: {str(e)}")
        
        finally:
            try:
                await tenant_service.delete_tenant(tenant.id)
            except:
                pass


class TestSecurityProperties:
    """Additional security-focused property tests."""
    
    @given(
        phone_numbers=st.lists(
            st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=('Nd',))),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, deadline=5000)
    def test_phone_number_hashing_consistency_property(self, phone_numbers):
        """
        Test that phone number hashing is consistent and secure.
        
        This property ensures that the same phone number always produces
        the same hash, but different numbers produce different hashes.
        """
        hashes = []
        
        for number in phone_numbers:
            # Add formatting variations
            formatted_numbers = [
                number,
                f"+1{number}",
                f"{number[:3]}-{number[3:6]}-{number[6:]}",
                f"({number[:3]}) {number[3:6]}-{number[6:]}"
            ]
            
            # All variations should produce the same hash
            number_hashes = [SecurityUtils.hash_phone_number(num) for num in formatted_numbers]
            
            # All hashes for the same number should be identical
            assert all(h == number_hashes[0] for h in number_hashes), f"All formats of {number} should produce same hash"
            
            # Hash should not contain original number
            for hash_val in number_hashes:
                assert number not in hash_val, f"Hash should not contain original number {number}"
            
            hashes.append(number_hashes[0])
        
        # All different numbers should produce different hashes
        unique_hashes = set(hashes)
        assert len(unique_hashes) == len(set(phone_numbers)), "Different numbers should produce different hashes"
    
    @given(
        request_data=st.dictionaries(
            keys=st.sampled_from([
                "user-agent", "accept", "accept-language", "accept-encoding",
                "connection", "host", "referer", "x-forwarded-for"
            ]),
            values=st.text(min_size=1, max_size=200),
            min_size=2,
            max_size=8
        )
    )
    @settings(max_examples=30, deadline=5000)
    def test_trusted_source_validation_property(self, request_data):
        """
        Test that trusted source validation works correctly without storing sensitive data.
        
        This property ensures that request validation doesn't rely on or store
        IP addresses or other sensitive information.
        """
        # Test trusted source validation
        is_trusted = SecurityUtils.is_request_from_trusted_source(request_data)
        
        # Should return a boolean
        assert isinstance(is_trusted, bool), "Trusted source check should return boolean"
        
        # Should work with minimal headers
        minimal_headers = {"user-agent": "test", "accept": "text/html"}
        minimal_result = SecurityUtils.is_request_from_trusted_source(minimal_headers)
        assert isinstance(minimal_result, bool), "Should work with minimal headers"
        
        # Should reject suspicious user agents
        suspicious_headers = {"user-agent": "bot crawler", "accept": "text/html"}
        suspicious_result = SecurityUtils.is_request_from_trusted_source(suspicious_headers)
        assert suspicious_result == False, "Should reject suspicious user agents"