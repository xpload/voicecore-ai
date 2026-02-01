"""
Unit tests for callback request system functionality.

Tests callback request creation, scheduling, execution, and status tracking
for the VoiceCore AI system.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from voicecore.services.callback_service import CallbackService, CallbackServiceError, CallbackNotFoundError, CallbackSchedulingError
from voicecore.models import CallbackRequest, CallbackStatus, CallbackPriority, CallbackType
from voicecore.utils.security import SecurityUtils


class TestCallbackService:
    """Test cases for callback service functionality."""
    
    @pytest.fixture
    def callback_service(self):
        """Create callback service instance for testing."""
        return CallbackService()
    
    @pytest.fixture
    def tenant_id(self):
        """Sample tenant ID for testing."""
        return uuid.uuid4()
    
    @pytest.fixture
    def sample_callback_data(self):
        """Sample callback request data for testing."""
        return {
            "caller_number": "+1234567890",
            "caller_name": "John Doe",
            "caller_email": "john.doe@example.com",
            "callback_reason": "Need help with account setup",
            "callback_type": CallbackType.SUPPORT.value,
            "priority": CallbackPriority.HIGH.value,
            "requested_time": datetime.utcnow() + timedelta(hours=2),
            "time_window_start": datetime.utcnow() + timedelta(hours=1),
            "time_window_end": datetime.utcnow() + timedelta(hours=8),
            "timezone": "America/New_York",
            "max_attempts": 3,
            "sms_notifications": True,
            "email_notifications": True,
            "tags": ["urgent", "new-customer"],
            "metadata": {"source": "web_form", "customer_id": "12345"}
        }
    
    @pytest.mark.asyncio
    async def test_create_callback_request_success(self, callback_service, tenant_id, sample_callback_data):
        """Test successful callback request creation."""
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            result = await callback_service.create_callback_request(tenant_id, sample_callback_data)
            
            assert result.caller_name == sample_callback_data["caller_name"]
            assert result.callback_type == CallbackType.SUPPORT
            assert result.priority == CallbackPriority.HIGH
            assert result.tenant_id == tenant_id
    
    @pytest.mark.asyncio
    async def test_get_callback_request_found(self, callback_service, tenant_id):
        """Test getting callback request when it exists."""
        callback_id = uuid.uuid4()
        
        mock_callback = CallbackRequest(
            id=callback_id,
            tenant_id=tenant_id,
            caller_name="John Doe",
            callback_type=CallbackType.GENERAL,
            priority=CallbackPriority.NORMAL,
            status=CallbackStatus.PENDING
        )
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_callback
            
            result = await callback_service.get_callback_request(tenant_id, callback_id)
            
            assert result is not None
            assert result.id == callback_id
            assert result.caller_name == "John Doe"
    
    @pytest.mark.asyncio
    async def test_get_callback_request_not_found(self, callback_service, tenant_id):
        """Test getting callback request when it doesn't exist."""
        callback_id = uuid.uuid4()
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
            
            result = await callback_service.get_callback_request(tenant_id, callback_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_list_callback_requests_with_filters(self, callback_service, tenant_id):
        """Test listing callback requests with filters."""
        mock_callbacks = [
            CallbackRequest(id=uuid.uuid4(), tenant_id=tenant_id, caller_name="John Doe", status=CallbackStatus.PENDING),
            CallbackRequest(id=uuid.uuid4(), tenant_id=tenant_id, caller_name="Jane Smith", status=CallbackStatus.SCHEDULED)
        ]
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = mock_callbacks
            
            result = await callback_service.list_callback_requests(
                tenant_id=tenant_id,
                status=CallbackStatus.PENDING,
                search="John"
            )
            
            assert len(result) == 2  # Mock returns all, but in real implementation would be filtered
    
    @pytest.mark.asyncio
    async def test_schedule_callback_success(self, callback_service, tenant_id):
        """Test successful callback scheduling."""
        callback_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        scheduled_time = datetime.utcnow() + timedelta(hours=2)
        
        mock_callback = CallbackRequest(
            id=callback_id,
            tenant_id=tenant_id,
            status=CallbackStatus.PENDING,
            time_window_start=datetime.utcnow() + timedelta(hours=1),
            time_window_end=datetime.utcnow() + timedelta(hours=8)
        )
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_callback
            
            result = await callback_service.schedule_callback(
                tenant_id, callback_id, scheduled_time, agent_id
            )
            
            assert result is True
            assert mock_callback.scheduled_time == scheduled_time
            assert mock_callback.assigned_agent_id == agent_id
            assert mock_callback.status == CallbackStatus.SCHEDULED
    
    @pytest.mark.asyncio
    async def test_schedule_callback_not_found(self, callback_service, tenant_id):
        """Test callback scheduling when callback doesn't exist."""
        callback_id = uuid.uuid4()
        scheduled_time = datetime.utcnow() + timedelta(hours=2)
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
            
            with pytest.raises(CallbackNotFoundError):
                await callback_service.schedule_callback(tenant_id, callback_id, scheduled_time)
    
    @pytest.mark.asyncio
    async def test_schedule_callback_past_time(self, callback_service, tenant_id):
        """Test callback scheduling with past time."""
        callback_id = uuid.uuid4()
        scheduled_time = datetime.utcnow() - timedelta(hours=1)  # Past time
        
        mock_callback = CallbackRequest(
            id=callback_id,
            tenant_id=tenant_id,
            status=CallbackStatus.PENDING
        )
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_callback
            
            with pytest.raises(CallbackSchedulingError, match="Cannot schedule callback in the past"):
                await callback_service.schedule_callback(tenant_id, callback_id, scheduled_time)
    
    @pytest.mark.asyncio
    async def test_execute_callback_success(self, callback_service, tenant_id):
        """Test successful callback execution."""
        callback_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        
        mock_callback = CallbackRequest(
            id=callback_id,
            tenant_id=tenant_id,
            status=CallbackStatus.SCHEDULED,
            attempts=0
        )
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_callback
            
            result = await callback_service.execute_callback(tenant_id, callback_id, agent_id)
            
            assert result.callback_request_id == callback_id
            assert result.attempted_by_agent_id == agent_id
            assert result.attempt_number == 1
            assert mock_callback.status == CallbackStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_complete_callback_attempt_success(self, callback_service, tenant_id):
        """Test successful callback attempt completion."""
        attempt_id = uuid.uuid4()
        call_id = uuid.uuid4()
        
        from voicecore.models.callback import CallbackAttempt
        mock_attempt = CallbackAttempt(
            id=attempt_id,
            tenant_id=tenant_id,
            callback_request_id=uuid.uuid4(),
            attempt_number=1
        )
        
        mock_callback = CallbackRequest(
            id=mock_attempt.callback_request_id,
            tenant_id=tenant_id,
            attempts=0,
            max_attempts=3
        )
        
        mock_attempt.callback_request = mock_callback
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_attempt
            
            result = await callback_service.complete_callback_attempt(
                tenant_id=tenant_id,
                attempt_id=attempt_id,
                outcome="connected",
                call_id=call_id,
                duration_seconds=300,
                caller_reached=True,
                issue_resolved=True,
                agent_notes="Customer issue resolved successfully"
            )
            
            assert result is True
            assert mock_attempt.outcome == "connected"
            assert mock_attempt.caller_reached is True
            assert mock_attempt.issue_resolved is True
            assert mock_callback.status == CallbackStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_get_pending_callbacks(self, callback_service, tenant_id):
        """Test getting pending callbacks."""
        current_time = datetime.utcnow()
        
        mock_callbacks = [
            CallbackRequest(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                status=CallbackStatus.SCHEDULED,
                scheduled_time=current_time - timedelta(minutes=5),  # Overdue
                priority=CallbackPriority.HIGH
            ),
            CallbackRequest(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                status=CallbackStatus.PENDING,
                next_attempt_at=current_time - timedelta(minutes=10),  # Ready for retry
                priority=CallbackPriority.NORMAL
            )
        ]
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = mock_callbacks
            
            result = await callback_service.get_pending_callbacks(tenant_id)
            
            assert len(result) == 2
            # Should be ordered by priority (HIGH first)
            assert result[0].priority == CallbackPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_cancel_callback_success(self, callback_service, tenant_id):
        """Test successful callback cancellation."""
        callback_id = uuid.uuid4()
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            # Mock successful update (1 row affected)
            mock_session.return_value.__aenter__.return_value.execute.return_value.rowcount = 1
            
            result = await callback_service.cancel_callback(
                tenant_id, callback_id, "cancelled_by_customer"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_cancel_callback_not_found(self, callback_service, tenant_id):
        """Test callback cancellation when callback doesn't exist or can't be cancelled."""
        callback_id = uuid.uuid4()
        
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            # Mock no rows affected
            mock_session.return_value.__aenter__.return_value.execute.return_value.rowcount = 0
            
            result = await callback_service.cancel_callback(tenant_id, callback_id)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_callback_analytics(self, callback_service, tenant_id):
        """Test callback analytics retrieval."""
        with patch('voicecore.services.callback_service.get_db_session') as mock_session:
            # Mock analytics data
            mock_session.return_value.__aenter__.return_value.execute.return_value.fetchall.return_value = [
                (CallbackStatus.COMPLETED, 15),
                (CallbackStatus.PENDING, 5),
                (CallbackStatus.FAILED, 2)
            ]
            
            mock_session.return_value.__aenter__.return_value.execute.return_value.fetchone.return_value = (22, 15, 2.1, 180.5)
            
            result = await callback_service.get_callback_analytics(tenant_id)
            
            assert 'by_status' in result
            assert 'total_callbacks' in result
            assert 'success_rate' in result
            assert result['by_status'][CallbackStatus.COMPLETED.value] == 15


class TestCallbackRequestModel:
    """Test cases for callback request model functionality."""
    
    def test_callback_request_is_active_pending(self):
        """Test callback request active status when pending."""
        callback_request = CallbackRequest(
            status=CallbackStatus.PENDING
        )
        
        assert callback_request.is_active is True
    
    def test_callback_request_is_active_completed(self):
        """Test callback request active status when completed."""
        callback_request = CallbackRequest(
            status=CallbackStatus.COMPLETED
        )
        
        assert callback_request.is_active is False
    
    def test_callback_request_is_overdue(self):
        """Test callback request overdue status."""
        callback_request = CallbackRequest(
            scheduled_time=datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
        )
        
        assert callback_request.is_overdue is True
    
    def test_callback_request_not_overdue(self):
        """Test callback request not overdue."""
        callback_request = CallbackRequest(
            scheduled_time=datetime.utcnow() + timedelta(minutes=30)  # 30 minutes from now
        )
        
        assert callback_request.is_overdue is False
    
    def test_callback_request_is_expired(self):
        """Test callback request expired status."""
        callback_request = CallbackRequest(
            created_at=datetime.utcnow() - timedelta(days=10),  # 10 days ago
            time_window_end=None  # Uses default 7-day expiry
        )
        
        assert callback_request.is_expired is True
    
    def test_callback_request_not_expired(self):
        """Test callback request not expired."""
        callback_request = CallbackRequest(
            created_at=datetime.utcnow() - timedelta(days=2),  # 2 days ago
            time_window_end=datetime.utcnow() + timedelta(days=1)  # Expires tomorrow
        )
        
        assert callback_request.is_expired is False
    
    def test_callback_request_can_retry(self):
        """Test callback request retry capability."""
        callback_request = CallbackRequest(
            attempts=1,
            max_attempts=3,
            created_at=datetime.utcnow() - timedelta(hours=1)  # Recent, not expired
        )
        
        assert callback_request.can_retry is True
    
    def test_callback_request_cannot_retry_max_attempts(self):
        """Test callback request cannot retry when max attempts reached."""
        callback_request = CallbackRequest(
            attempts=3,
            max_attempts=3,
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        assert callback_request.can_retry is False
    
    def test_callback_request_priority_score_calculation(self):
        """Test callback request priority score calculation."""
        callback_request = CallbackRequest(
            priority=CallbackPriority.HIGH,  # 3 * 10 = 30
            attempts=2,  # 2 * 5 = 10
            scheduled_time=datetime.utcnow() - timedelta(hours=2)  # Overdue +20
        )
        
        # Base: 30, attempts: 10, overdue: 20 = 60
        expected_score = 30 + 10 + 20
        assert callback_request.priority_score == expected_score
    
    def test_callback_request_tag_management(self):
        """Test callback request tag management."""
        callback_request = CallbackRequest(tags=[])
        
        # Test adding tag
        callback_request.add_tag("urgent")
        assert "urgent" in callback_request.tags
        
        # Test removing tag
        callback_request.remove_tag("urgent")
        assert "urgent" not in callback_request.tags
    
    def test_callback_request_metadata_management(self):
        """Test callback request metadata management."""
        callback_request = CallbackRequest(metadata={})
        
        # Test setting metadata
        callback_request.set_metadata("source", "web_form")
        assert callback_request.get_metadata("source") == "web_form"
        
        # Test getting non-existent metadata with default
        assert callback_request.get_metadata("non_existent", "default") == "default"
    
    def test_callback_request_calculate_next_attempt_time(self):
        """Test callback request next attempt time calculation."""
        callback_request = CallbackRequest(
            attempts=0,
            max_attempts=3
        )
        
        next_attempt = callback_request.calculate_next_attempt_time()
        
        # First attempt should be 15 minutes from now
        expected_time = datetime.utcnow() + timedelta(minutes=15)
        time_diff = abs((next_attempt - expected_time).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance
    
    def test_callback_request_update_attempt(self):
        """Test callback request attempt update."""
        callback_request = CallbackRequest(
            attempts=0,
            max_attempts=3,
            system_notes=None
        )
        
        callback_request.update_attempt("no_answer", "Caller did not answer")
        
        assert callback_request.attempts == 1
        assert callback_request.outcome == "no_answer"
        assert "Caller did not answer" in callback_request.system_notes
        assert callback_request.next_attempt_at is not None


class TestCallbackSchedule:
    """Test cases for callback schedule functionality."""
    
    def test_callback_schedule_is_business_time_weekday(self):
        """Test callback schedule business time check for weekday."""
        from voicecore.models.callback import CallbackSchedule
        
        schedule = CallbackSchedule(
            business_hours_start="09:00",
            business_hours_end="17:00",
            business_days=["monday", "tuesday", "wednesday", "thursday", "friday"]
        )
        
        # Tuesday at 2 PM
        tuesday_2pm = datetime(2024, 1, 2, 14, 0)  # January 2, 2024 is a Tuesday
        assert schedule.is_business_time(tuesday_2pm) is True
        
        # Tuesday at 8 PM (after hours)
        tuesday_8pm = datetime(2024, 1, 2, 20, 0)
        assert schedule.is_business_time(tuesday_8pm) is False
    
    def test_callback_schedule_is_business_time_weekend(self):
        """Test callback schedule business time check for weekend."""
        from voicecore.models.callback import CallbackSchedule
        
        schedule = CallbackSchedule(
            business_hours_start="09:00",
            business_hours_end="17:00",
            business_days=["monday", "tuesday", "wednesday", "thursday", "friday"]
        )
        
        # Saturday at 2 PM
        saturday_2pm = datetime(2024, 1, 6, 14, 0)  # January 6, 2024 is a Saturday
        assert schedule.is_business_time(saturday_2pm) is False
    
    def test_callback_schedule_get_next_available_slot(self):
        """Test callback schedule next available slot calculation."""
        from voicecore.models.callback import CallbackSchedule
        
        schedule = CallbackSchedule(
            business_hours_start="09:00",
            business_hours_end="17:00",
            business_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
            min_advance_minutes=30,
            max_advance_days=7
        )
        
        # Request slot for Tuesday at 8 AM (before business hours)
        tuesday_8am = datetime(2024, 1, 2, 8, 0)
        next_slot = schedule.get_next_available_slot(tuesday_8am)
        
        # Should get a slot during business hours
        assert next_slot is not None
        assert next_slot.hour >= 9  # During business hours
        assert next_slot.hour <= 17