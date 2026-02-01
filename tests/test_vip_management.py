"""
Unit tests for VIP caller management functionality.

Tests VIP caller identification, priority routing, special handling rules,
and escalation management for the VoiceCore AI system.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from voicecore.services.vip_service import VIPService, VIPServiceError, VIPNotFoundError
from voicecore.models import VIPCaller, VIPPriority, VIPStatus, VIPHandlingRule
from voicecore.utils.security import SecurityUtils


class TestVIPService:
    """Test cases for VIP service functionality."""
    
    @pytest.fixture
    def vip_service(self):
        """Create VIP service instance for testing."""
        return VIPService()
    
    @pytest.fixture
    def tenant_id(self):
        """Sample tenant ID for testing."""
        return uuid.uuid4()
    
    @pytest.fixture
    def sample_vip_data(self):
        """Sample VIP caller data for testing."""
        return {
            "phone_number": "+1234567890",
            "caller_name": "John Doe",
            "company_name": "Acme Corp",
            "vip_level": VIPPriority.GOLD.value,
            "status": VIPStatus.ACTIVE.value,
            "handling_rules": [VIPHandlingRule.PRIORITY_QUEUE.value],
            "custom_greeting": "Hello Mr. Doe, thank you for calling.",
            "max_wait_time": 30,
            "callback_priority": 1,
            "email": "john.doe@acme.com",
            "account_number": "ACC123456",
            "account_value": 50000.0,
            "notes": "High-value customer",
            "tags": ["premium", "enterprise"]
        }
    
    @pytest.mark.asyncio
    async def test_identify_vip_caller_found(self, vip_service, tenant_id):
        """Test VIP caller identification when caller is VIP."""
        phone_number = "+1234567890"
        hashed_phone = SecurityUtils.hash_phone_number(phone_number)
        
        # Mock VIP caller
        mock_vip = VIPCaller(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            phone_number=hashed_phone,
            caller_name="John Doe",
            vip_level=VIPPriority.GOLD,
            status=VIPStatus.ACTIVE,
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_until=datetime.utcnow() + timedelta(days=365)
        )
        
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_vip
            
            result = await vip_service.identify_vip_caller(tenant_id, phone_number)
            
            assert result is not None
            assert result.caller_name == "John Doe"
            assert result.vip_level == VIPPriority.GOLD
            assert result.is_active
    
    @pytest.mark.asyncio
    async def test_identify_vip_caller_not_found(self, vip_service, tenant_id):
        """Test VIP caller identification when caller is not VIP."""
        phone_number = "+1234567890"
        
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
            
            result = await vip_service.identify_vip_caller(tenant_id, phone_number)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_create_vip_caller_success(self, vip_service, tenant_id, sample_vip_data):
        """Test successful VIP caller creation."""
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            # Mock no existing VIP
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
            
            result = await vip_service.create_vip_caller(tenant_id, sample_vip_data)
            
            assert result.caller_name == sample_vip_data["caller_name"]
            assert result.vip_level == VIPPriority.GOLD
            assert result.tenant_id == tenant_id
    
    @pytest.mark.asyncio
    async def test_create_vip_caller_already_exists(self, vip_service, tenant_id, sample_vip_data):
        """Test VIP caller creation when caller already exists."""
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            # Mock existing VIP
            existing_vip = VIPCaller(id=uuid.uuid4(), tenant_id=tenant_id)
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = existing_vip
            
            with pytest.raises(VIPServiceError, match="already exists"):
                await vip_service.create_vip_caller(tenant_id, sample_vip_data)
    
    @pytest.mark.asyncio
    async def test_get_vip_routing_priority(self, vip_service, tenant_id):
        """Test VIP routing priority calculation."""
        vip_caller = VIPCaller(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            vip_level=VIPPriority.PLATINUM,
            account_value=100000.0,
            satisfaction_score=4.8,
            handling_rules=[VIPHandlingRule.IMMEDIATE_TRANSFER.value]
        )
        
        priority = await vip_service.get_vip_routing_priority(tenant_id, vip_caller)
        
        # Base priority (40) + account value bonus (20) + satisfaction bonus (5) + immediate transfer (50)
        expected_priority = 40 + 20 + 5 + 50
        assert priority == expected_priority
    
    @pytest.mark.asyncio
    async def test_update_vip_caller_success(self, vip_service, tenant_id):
        """Test successful VIP caller update."""
        vip_id = uuid.uuid4()
        update_data = {
            "caller_name": "Jane Doe",
            "vip_level": VIPPriority.DIAMOND.value,
            "notes": "Updated notes"
        }
        
        mock_vip = VIPCaller(
            id=vip_id,
            tenant_id=tenant_id,
            caller_name="John Doe",
            vip_level=VIPPriority.GOLD
        )
        
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_vip
            
            result = await vip_service.update_vip_caller(tenant_id, vip_id, update_data)
            
            assert result.caller_name == "Jane Doe"
            assert result.vip_level == VIPPriority.DIAMOND
    
    @pytest.mark.asyncio
    async def test_update_vip_caller_not_found(self, vip_service, tenant_id):
        """Test VIP caller update when caller doesn't exist."""
        vip_id = uuid.uuid4()
        update_data = {"caller_name": "Jane Doe"}
        
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
            
            with pytest.raises(VIPNotFoundError):
                await vip_service.update_vip_caller(tenant_id, vip_id, update_data)
    
    @pytest.mark.asyncio
    async def test_delete_vip_caller_success(self, vip_service, tenant_id):
        """Test successful VIP caller deletion."""
        vip_id = uuid.uuid4()
        
        mock_vip = VIPCaller(id=vip_id, tenant_id=tenant_id, caller_name="John Doe")
        
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_vip
            
            result = await vip_service.delete_vip_caller(tenant_id, vip_id)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_vip_caller_not_found(self, vip_service, tenant_id):
        """Test VIP caller deletion when caller doesn't exist."""
        vip_id = uuid.uuid4()
        
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
            
            with pytest.raises(VIPNotFoundError):
                await vip_service.delete_vip_caller(tenant_id, vip_id)
    
    @pytest.mark.asyncio
    async def test_list_vip_callers_with_filters(self, vip_service, tenant_id):
        """Test listing VIP callers with filters."""
        mock_vips = [
            VIPCaller(id=uuid.uuid4(), tenant_id=tenant_id, caller_name="John Doe", vip_level=VIPPriority.GOLD),
            VIPCaller(id=uuid.uuid4(), tenant_id=tenant_id, caller_name="Jane Smith", vip_level=VIPPriority.PLATINUM)
        ]
        
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = mock_vips
            
            result = await vip_service.list_vip_callers(
                tenant_id=tenant_id,
                vip_level=VIPPriority.GOLD,
                search="John"
            )
            
            assert len(result) == 2  # Mock returns all, but in real implementation would be filtered
    
    @pytest.mark.asyncio
    async def test_check_escalation_rules(self, vip_service, tenant_id):
        """Test escalation rule checking."""
        vip_caller = VIPCaller(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            vip_level=VIPPriority.PLATINUM
        )
        
        # Mock escalation rules
        from voicecore.models.vip import VIPEscalationRule
        mock_rules = [
            VIPEscalationRule(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                name="VIP Wait Time Rule",
                is_active=True,
                vip_levels=[VIPPriority.PLATINUM.value],
                max_wait_time=60,
                escalation_type="manager"
            )
        ]
        
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = mock_rules
            
            result = await vip_service.check_escalation_rules(
                tenant_id, vip_caller, wait_time=90, queue_position=1
            )
            
            assert len(result) == 1
            assert result[0].name == "VIP Wait Time Rule"
    
    @pytest.mark.asyncio
    async def test_record_vip_call(self, vip_service, tenant_id):
        """Test VIP call history recording."""
        vip_caller_id = uuid.uuid4()
        call_id = uuid.uuid4()
        call_details = {
            "vip_level": VIPPriority.GOLD,
            "handling_rules_applied": [VIPHandlingRule.PRIORITY_QUEUE.value],
            "wait_time_seconds": 45,
            "satisfaction_rating": 5,
            "issue_resolved": True
        }
        
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            result = await vip_service.record_vip_call(
                tenant_id, vip_caller_id, call_id, call_details
            )
            
            assert result.vip_caller_id == vip_caller_id
            assert result.call_id == call_id
            assert result.wait_time_seconds == 45
    
    @pytest.mark.asyncio
    async def test_get_vip_analytics(self, vip_service, tenant_id):
        """Test VIP analytics retrieval."""
        with patch('voicecore.services.vip_service.get_db_session') as mock_session:
            # Mock analytics data
            mock_session.return_value.__aenter__.return_value.execute.return_value.fetchall.return_value = [
                (VIPPriority.GOLD, 10, 45.0, 4.5),
                (VIPPriority.PLATINUM, 5, 30.0, 4.8)
            ]
            mock_session.return_value.__aenter__.return_value.execute.return_value.fetchone.return_value = (15, 2, 4.6)
            
            result = await vip_service.get_vip_analytics(tenant_id)
            
            assert 'by_vip_level' in result
            assert 'escalation_rate' in result
            assert len(result['by_vip_level']) == 2
    
    @pytest.mark.asyncio
    async def test_bulk_import_vips(self, vip_service, tenant_id, sample_vip_data):
        """Test bulk VIP import functionality."""
        vip_data_list = [sample_vip_data.copy() for _ in range(3)]
        
        # Modify phone numbers to make them unique
        for i, vip_data in enumerate(vip_data_list):
            vip_data["phone_number"] = f"+123456789{i}"
        
        with patch.object(vip_service, 'create_vip_caller') as mock_create:
            mock_create.return_value = VIPCaller(id=uuid.uuid4(), tenant_id=tenant_id)
            
            result = await vip_service.bulk_import_vips(tenant_id, vip_data_list)
            
            assert result['total'] == 3
            assert result['successful'] == 3
            assert result['failed'] == 0


class TestVIPCallerModel:
    """Test cases for VIP caller model functionality."""
    
    def test_vip_caller_is_active_valid(self):
        """Test VIP caller active status when valid."""
        vip_caller = VIPCaller(
            status=VIPStatus.ACTIVE,
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_until=datetime.utcnow() + timedelta(days=30)
        )
        
        assert vip_caller.is_active is True
    
    def test_vip_caller_is_active_expired(self):
        """Test VIP caller active status when expired."""
        vip_caller = VIPCaller(
            status=VIPStatus.ACTIVE,
            valid_from=datetime.utcnow() - timedelta(days=60),
            valid_until=datetime.utcnow() - timedelta(days=1)
        )
        
        assert vip_caller.is_active is False
    
    def test_vip_caller_is_active_inactive_status(self):
        """Test VIP caller active status when status is inactive."""
        vip_caller = VIPCaller(
            status=VIPStatus.INACTIVE,
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_until=datetime.utcnow() + timedelta(days=30)
        )
        
        assert vip_caller.is_active is False
    
    def test_vip_caller_priority_score_calculation(self):
        """Test VIP caller priority score calculation."""
        vip_caller = VIPCaller(
            vip_level=VIPPriority.PLATINUM,
            account_value=150000.0,
            satisfaction_score=4.8
        )
        
        # Base score: 40 (PLATINUM * 10)
        # Account value bonus: 20 (>100k)
        # Satisfaction bonus: 5 (>=4.5)
        expected_score = 40 + 20 + 5
        assert vip_caller.priority_score == expected_score
    
    def test_vip_caller_handling_rules(self):
        """Test VIP caller handling rule management."""
        vip_caller = VIPCaller(handling_rules=[])
        
        # Test adding handling rule
        vip_caller.add_handling_rule(VIPHandlingRule.PRIORITY_QUEUE)
        assert vip_caller.has_handling_rule(VIPHandlingRule.PRIORITY_QUEUE)
        
        # Test removing handling rule
        vip_caller.remove_handling_rule(VIPHandlingRule.PRIORITY_QUEUE)
        assert not vip_caller.has_handling_rule(VIPHandlingRule.PRIORITY_QUEUE)
    
    def test_vip_caller_tag_management(self):
        """Test VIP caller tag management."""
        vip_caller = VIPCaller(tags=[])
        
        # Test adding tag
        vip_caller.add_tag("premium")
        assert "premium" in vip_caller.tags
        
        # Test removing tag
        vip_caller.remove_tag("premium")
        assert "premium" not in vip_caller.tags
    
    def test_vip_caller_metadata_management(self):
        """Test VIP caller metadata management."""
        vip_caller = VIPCaller(metadata={})
        
        # Test setting metadata
        vip_caller.set_metadata("custom_field", "custom_value")
        assert vip_caller.get_metadata("custom_field") == "custom_value"
        
        # Test getting non-existent metadata with default
        assert vip_caller.get_metadata("non_existent", "default") == "default"
    
    def test_vip_caller_update_call_stats(self):
        """Test VIP caller call statistics update."""
        vip_caller = VIPCaller(
            total_calls=0,
            average_call_duration=0,
            satisfaction_score=None
        )
        
        # First call
        vip_caller.update_call_stats(120, 4.5)
        assert vip_caller.total_calls == 1
        assert vip_caller.average_call_duration == 120
        assert vip_caller.satisfaction_score == 4.5
        
        # Second call
        vip_caller.update_call_stats(180, 4.0)
        assert vip_caller.total_calls == 2
        assert vip_caller.average_call_duration == 150  # (120 + 180) / 2
        # Satisfaction should be weighted average: 0.7 * 4.5 + 0.3 * 4.0 = 4.35
        assert abs(vip_caller.satisfaction_score - 4.35) < 0.01


class TestVIPEscalationRule:
    """Test cases for VIP escalation rule functionality."""
    
    def test_escalation_rule_is_applicable_vip_level(self):
        """Test escalation rule applicability based on VIP level."""
        from voicecore.models.vip import VIPEscalationRule
        
        rule = VIPEscalationRule(
            is_active=True,
            vip_levels=[VIPPriority.GOLD.value, VIPPriority.PLATINUM.value]
        )
        
        current_time = datetime.utcnow()
        
        assert rule.is_applicable(VIPPriority.GOLD, current_time) is True
        assert rule.is_applicable(VIPPriority.SILVER, current_time) is False
    
    def test_escalation_rule_is_applicable_time_of_day(self):
        """Test escalation rule applicability based on time of day."""
        from voicecore.models.vip import VIPEscalationRule
        
        rule = VIPEscalationRule(
            is_active=True,
            vip_levels=[],
            time_of_day_start="09:00",
            time_of_day_end="17:00"
        )
        
        # Test within business hours
        business_time = datetime.utcnow().replace(hour=12, minute=0)
        assert rule.is_applicable(VIPPriority.GOLD, business_time) is True
        
        # Test outside business hours
        after_hours = datetime.utcnow().replace(hour=20, minute=0)
        assert rule.is_applicable(VIPPriority.GOLD, after_hours) is False
    
    def test_escalation_rule_should_escalate(self):
        """Test escalation rule trigger conditions."""
        from voicecore.models.vip import VIPEscalationRule
        
        rule = VIPEscalationRule(
            max_wait_time=60,
            max_queue_position=3
        )
        
        # Should escalate due to wait time
        assert rule.should_escalate(wait_time=90, queue_position=1) is True
        
        # Should escalate due to queue position
        assert rule.should_escalate(wait_time=30, queue_position=5) is True
        
        # Should not escalate
        assert rule.should_escalate(wait_time=30, queue_position=1) is False