"""
Integration tests for external service integrations.

Tests integration with Twilio, OpenAI, and other external services
to ensure proper error handling, failover, and service reliability.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from voicecore.services.twilio_service import TwilioService
from voicecore.services.openai_service import OpenAIService
from voicecore.services.call_routing_service import CallRoutingService
from voicecore.services.error_handling_service import ErrorHandlingService
from voicecore.services.high_availability_service import HighAvailabilityService
from voicecore.models.tenant import Tenant
from voicecore.models.call import Call, CallStatus


@pytest.fixture
async def test_tenant(db_session: AsyncSession):
    """Create a test tenant for external service tests."""
    from voicecore.services.tenant_service import TenantService
    
    tenant_service = TenantService()
    
    tenant_data = {
        "company_name": "External Test Company",
        "domain": "external-test.com",
        "phone_number": "+1555000111",
        "ai_name": "TestAI",
        "ai_voice": "alloy",
        "business_hours_start": "09:00",
        "business_hours_end": "17:00",
        "timezone": "UTC"
    }
    
    tenant = await tenant_service.create_tenant(tenant_data)
    yield tenant
    
    # Cleanup
    await tenant_service.delete_tenant(tenant.id)


class TestTwilioIntegration:
    """Test Twilio service integration and error handling."""
    
    @pytest.mark.asyncio
    async def test_twilio_call_creation_success(self, test_tenant):
        """Test successful Twilio call creation."""
        
        with patch('twilio.rest.Client') as mock_client:
            # Mock successful Twilio response
            mock_call = MagicMock()
            mock_call.sid = "CA123456789abcdef"
            mock_call.status = "in-progress"
            mock_call.from_ = "+1234567890"
            mock_call.to = test_tenant.phone_number
            
            mock_client.return_value.calls.create.return_value = mock_call
            
            twilio_service = TwilioService()
            
            call_data = {
                "from_number": "+1234567890",
                "to_number": test_tenant.phone_number,
                "webhook_url": "https://api.example.com/webhook"
            }
            
            result = await twilio_service.create_call(call_data)
            
            assert result["success"] is True
            assert result["call_sid"] == "CA123456789abcdef"
            assert result["status"] == "in-progress"
            
            # Verify Twilio client was called correctly
            mock_client.return_value.calls.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_twilio_call_creation_failure(self, test_tenant):
        """Test Twilio call creation failure handling."""
        
        with patch('twilio.rest.Client') as mock_client:
            # Mock Twilio exception
            from twilio.base.exceptions import TwilioRestException
            
            mock_client.return_value.calls.create.side_effect = TwilioRestException(
                status=400,
                uri="/Calls",
                msg="Invalid phone number"
            )
            
            twilio_service = TwilioService()
            
            call_data = {
                "from_number": "invalid",
                "to_number": test_tenant.phone_number,
                "webhook_url": "https://api.example.com/webhook"
            }
            
            result = await twilio_service.create_call(call_data)
            
            assert result["success"] is False
            assert "Invalid phone number" in result["error"]
            assert result["error_code"] == 400
    
    @pytest.mark.asyncio
    async def test_twilio_call_transfer_success(self, test_tenant):
        """Test successful call transfer via Twilio."""
        
        with patch('twilio.rest.Client') as mock_client:
            # Mock successful transfer
            mock_call = MagicMock()
            mock_call.update.return_value = True
            
            mock_client.return_value.calls.return_value.get.return_value = mock_call
            
            twilio_service = TwilioService()
            
            transfer_data = {
                "call_sid": "CA123456789",
                "transfer_to": "+1987654321",
                "transfer_url": "https://api.example.com/transfer"
            }
            
            result = await twilio_service.transfer_call(transfer_data)
            
            assert result["success"] is True
            assert result["transferred"] is True
    
    @pytest.mark.asyncio
    async def test_twilio_webhook_validation(self, test_tenant):
        """Test Twilio webhook signature validation."""
        
        twilio_service = TwilioService()
        
        # Mock webhook data
        webhook_data = {
            "CallSid": "CA123456789",
            "CallStatus": "completed",
            "From": "+1234567890",
            "To": test_tenant.phone_number
        }
        
        # Mock valid signature
        with patch('twilio.request_validator.RequestValidator') as mock_validator:
            mock_validator.return_value.validate.return_value = True
            
            is_valid = await twilio_service.validate_webhook(
                webhook_data,
                "https://api.example.com/webhook",
                "test_signature"
            )
            
            assert is_valid is True
        
        # Mock invalid signature
        with patch('twilio.request_validator.RequestValidator') as mock_validator:
            mock_validator.return_value.validate.return_value = False
            
            is_valid = await twilio_service.validate_webhook(
                webhook_data,
                "https://api.example.com/webhook",
                "invalid_signature"
            )
            
            assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_twilio_service_retry_logic(self, test_tenant):
        """Test Twilio service retry logic on temporary failures."""
        
        with patch('twilio.rest.Client') as mock_client:
            # Mock temporary failure then success
            from twilio.base.exceptions import TwilioRestException
            
            call_count = 0
            
            def mock_create_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count < 3:  # Fail first 2 attempts
                    raise TwilioRestException(
                        status=503,
                        uri="/Calls",
                        msg="Service temporarily unavailable"
                    )
                
                # Success on 3rd attempt
                mock_call = MagicMock()
                mock_call.sid = "CA123456789"
                mock_call.status = "in-progress"
                return mock_call
            
            mock_client.return_value.calls.create.side_effect = mock_create_call
            
            twilio_service = TwilioService()
            
            call_data = {
                "from_number": "+1234567890",
                "to_number": test_tenant.phone_number,
                "webhook_url": "https://api.example.com/webhook"
            }
            
            result = await twilio_service.create_call_with_retry(call_data, max_retries=3)
            
            assert result["success"] is True
            assert result["call_sid"] == "CA123456789"
            assert call_count == 3  # Should have retried 3 times


class TestOpenAIIntegration:
    """Test OpenAI service integration and error handling."""
    
    @pytest.mark.asyncio
    async def test_openai_conversation_success(self, test_tenant):
        """Test successful OpenAI conversation processing."""
        
        with patch('openai.AsyncOpenAI') as mock_client:
            # Mock successful OpenAI response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Hello! How can I help you today?"
            mock_response.usage.total_tokens = 50
            
            mock_client.return_value.chat.completions.create.return_value = mock_response
            
            openai_service = OpenAIService()
            
            conversation_data = {
                "messages": [
                    {"role": "user", "content": "Hi, I need help with my account"}
                ],
                "tenant_id": test_tenant.id,
                "call_id": str(uuid.uuid4())
            }
            
            result = await openai_service.process_conversation(conversation_data)
            
            assert result["success"] is True
            assert result["response"] == "Hello! How can I help you today?"
            assert result["tokens_used"] == 50
    
    @pytest.mark.asyncio
    async def test_openai_conversation_failure(self, test_tenant):
        """Test OpenAI conversation failure handling."""
        
        with patch('openai.AsyncOpenAI') as mock_client:
            # Mock OpenAI exception
            import openai
            
            mock_client.return_value.chat.completions.create.side_effect = openai.RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(),
                body={}
            )
            
            openai_service = OpenAIService()
            
            conversation_data = {
                "messages": [
                    {"role": "user", "content": "Hi, I need help"}
                ],
                "tenant_id": test_tenant.id,
                "call_id": str(uuid.uuid4())
            }
            
            result = await openai_service.process_conversation(conversation_data)
            
            assert result["success"] is False
            assert "rate limit" in result["error"].lower()
            assert result["fallback_response"] is not None
    
    @pytest.mark.asyncio
    async def test_openai_realtime_api_connection(self, test_tenant):
        """Test OpenAI Realtime API WebSocket connection."""
        
        with patch('websockets.connect') as mock_connect:
            # Mock WebSocket connection
            mock_websocket = AsyncMock()
            mock_websocket.send = AsyncMock()
            mock_websocket.recv = AsyncMock(return_value='{"type": "session.created"}')
            
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            
            openai_service = OpenAIService()
            
            session_data = {
                "tenant_id": test_tenant.id,
                "call_id": str(uuid.uuid4()),
                "voice": "alloy"
            }
            
            result = await openai_service.create_realtime_session(session_data)
            
            assert result["success"] is True
            assert result["session_id"] is not None
            
            # Verify WebSocket connection was established
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_openai_intent_analysis(self, test_tenant):
        """Test OpenAI intent analysis functionality."""
        
        with patch('openai.AsyncOpenAI') as mock_client:
            # Mock intent analysis response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"intent": "billing_inquiry", "confidence": 0.95, "entities": {"account_type": "premium"}}'
            
            mock_client.return_value.chat.completions.create.return_value = mock_response
            
            openai_service = OpenAIService()
            
            analysis_data = {
                "text": "I have a question about my premium account billing",
                "tenant_id": test_tenant.id,
                "context": {"previous_intents": []}
            }
            
            result = await openai_service.analyze_intent(analysis_data)
            
            assert result["success"] is True
            assert result["intent"] == "billing_inquiry"
            assert result["confidence"] == 0.95
            assert result["entities"]["account_type"] == "premium"
    
    @pytest.mark.asyncio
    async def test_openai_service_failover(self, test_tenant):
        """Test OpenAI service failover to backup model."""
        
        with patch('openai.AsyncOpenAI') as mock_client:
            # Mock primary model failure
            import openai
            
            call_count = 0
            
            def mock_create_completion(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count == 1:  # Primary model fails
                    raise openai.APIError(
                        message="Model unavailable",
                        request=MagicMock(),
                        body={}
                    )
                
                # Backup model succeeds
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "I apologize for the delay. How can I help you?"
                return mock_response
            
            mock_client.return_value.chat.completions.create.side_effect = mock_create_completion
            
            openai_service = OpenAIService()
            
            conversation_data = {
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "tenant_id": test_tenant.id,
                "call_id": str(uuid.uuid4())
            }
            
            result = await openai_service.process_conversation_with_failover(conversation_data)
            
            assert result["success"] is True
            assert "apologize for the delay" in result["response"]
            assert result["model_used"] == "backup"
            assert call_count == 2  # Primary failed, backup succeeded


class TestServiceIntegrationResilience:
    """Test service integration resilience and error recovery."""
    
    @pytest.mark.asyncio
    async def test_call_flow_with_service_failures(self, test_tenant):
        """Test complete call flow with various service failures."""
        
        call_routing_service = CallRoutingService()
        error_handling_service = ErrorHandlingService()
        
        # Mock partial service failures
        with patch('voicecore.services.twilio_service.TwilioService') as mock_twilio, \
             patch('voicecore.services.openai_service.OpenAIService') as mock_openai:
            
            # Twilio works, OpenAI fails initially
            mock_twilio_instance = AsyncMock()
            mock_twilio.return_value = mock_twilio_instance
            mock_twilio_instance.create_call.return_value = {
                "success": True,
                "call_sid": "CA123456789"
            }
            
            mock_openai_instance = AsyncMock()
            mock_openai.return_value = mock_openai_instance
            
            # OpenAI fails first, succeeds on retry
            call_count = 0
            
            async def mock_process_conversation(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count == 1:
                    raise Exception("OpenAI service unavailable")
                
                return {
                    "success": True,
                    "response": "Hello! I'm back online. How can I help?",
                    "action": "continue"
                }
            
            mock_openai_instance.process_conversation.side_effect = mock_process_conversation
            
            # Incoming call
            call_data = {
                "from_number": "+1234567890",
                "to_number": test_tenant.phone_number,
                "twilio_call_sid": "CA123456789",
                "tenant_id": test_tenant.id
            }
            
            call = await call_routing_service.handle_incoming_call(call_data)
            
            # First AI interaction fails, should trigger error handling
            conversation_data = {
                "call_id": call.id,
                "message": "Hello, I need help",
                "timestamp": datetime.utcnow()
            }
            
            # Should handle error gracefully and retry
            ai_response = await call_routing_service.process_ai_interaction_with_retry(
                call.id, conversation_data
            )
            
            assert ai_response["success"] is True
            assert "back online" in ai_response["response"]
            assert call_count == 2  # Failed once, succeeded on retry
    
    @pytest.mark.asyncio
    async def test_high_availability_failover(self, test_tenant):
        """Test high availability failover mechanisms."""
        
        ha_service = HighAvailabilityService()
        
        # Mock primary region failure
        with patch('voicecore.services.twilio_service.TwilioService') as mock_twilio:
            
            call_count = 0
            
            async def mock_create_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count <= 2:  # Primary region fails
                    raise Exception("Primary region unavailable")
                
                # Backup region succeeds
                return {
                    "success": True,
                    "call_sid": "CA_BACKUP_123",
                    "region": "backup"
                }
            
            mock_twilio.return_value.create_call.side_effect = mock_create_call
            
            call_data = {
                "from_number": "+1234567890",
                "to_number": test_tenant.phone_number,
                "tenant_id": test_tenant.id
            }
            
            result = await ha_service.create_call_with_failover(call_data)
            
            assert result["success"] is True
            assert result["call_sid"] == "CA_BACKUP_123"
            assert result["region"] == "backup"
            assert call_count == 3  # Failed twice, succeeded on backup
    
    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, test_tenant):
        """Test service health monitoring and alerting."""
        
        error_handling_service = ErrorHandlingService()
        
        # Simulate service health checks
        services = ["twilio", "openai", "database", "redis"]
        
        health_results = {}
        
        for service in services:
            health_check = await error_handling_service.check_service_health(service)
            health_results[service] = health_check
        
        # All services should be healthy in test environment
        for service, health in health_results.items():
            assert health["status"] == "healthy"
            assert health["response_time"] < 1000  # Less than 1 second
            assert health["last_check"] is not None
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, test_tenant):
        """Test circuit breaker pattern for external services."""
        
        from voicecore.services.circuit_breaker import CircuitBreaker
        
        # Mock failing service
        failure_count = 0
        
        async def failing_service():
            nonlocal failure_count
            failure_count += 1
            
            if failure_count <= 5:  # Fail first 5 calls
                raise Exception("Service unavailable")
            
            return {"success": True, "data": "Service recovered"}
        
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,
            expected_exception=Exception
        )
        
        # First 3 calls should fail and open circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_service)
        
        # Circuit should be open now
        assert circuit_breaker.state == "open"
        
        # Next call should fail fast (circuit open)
        with pytest.raises(Exception) as exc_info:
            await circuit_breaker.call(failing_service)
        
        assert "Circuit breaker is open" in str(exc_info.value)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Circuit should be half-open, next call should succeed
        result = await circuit_breaker.call(failing_service)
        
        assert result["success"] is True
        assert circuit_breaker.state == "closed"
    
    @pytest.mark.asyncio
    async def test_service_rate_limiting(self, test_tenant):
        """Test rate limiting for external service calls."""
        
        from voicecore.services.rate_limiter import RateLimiter
        
        # Create rate limiter: 5 calls per second
        rate_limiter = RateLimiter(max_calls=5, time_window=1)
        
        async def mock_api_call():
            return {"success": True, "timestamp": datetime.utcnow()}
        
        # Make 5 calls quickly - should all succeed
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                rate_limiter.execute(mock_api_call)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for result in results:
            assert result["success"] is True
        
        # 6th call should be rate limited
        with pytest.raises(Exception) as exc_info:
            await rate_limiter.execute(mock_api_call)
        
        assert "Rate limit exceeded" in str(exc_info.value)
        
        # Wait for rate limit window to reset
        await asyncio.sleep(1.1)
        
        # Should be able to make calls again
        result = await rate_limiter.execute(mock_api_call)
        assert result["success"] is True


class TestServiceMetricsAndMonitoring:
    """Test service metrics collection and monitoring."""
    
    @pytest.mark.asyncio
    async def test_service_performance_metrics(self, test_tenant):
        """Test collection of service performance metrics."""
        
        from voicecore.services.performance_monitoring_service import PerformanceMonitoringService
        
        monitoring_service = PerformanceMonitoringService()
        
        # Mock service calls with different performance characteristics
        with patch('voicecore.services.twilio_service.TwilioService') as mock_twilio:
            
            async def mock_slow_call(*args, **kwargs):
                await asyncio.sleep(0.5)  # Simulate slow call
                return {"success": True, "call_sid": "CA123"}
            
            async def mock_fast_call(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate fast call
                return {"success": True, "call_sid": "CA456"}
            
            mock_twilio.return_value.create_call.side_effect = mock_slow_call
            
            # Monitor slow call
            start_time = datetime.utcnow()
            
            with monitoring_service.monitor_service_call("twilio", "create_call"):
                result = await mock_twilio.return_value.create_call({})
            
            end_time = datetime.utcnow()
            
            # Get metrics
            metrics = await monitoring_service.get_service_metrics("twilio")
            
            assert metrics["total_calls"] >= 1
            assert metrics["average_response_time"] >= 500  # Should be around 500ms
            assert metrics["success_rate"] == 100.0
        
        # Test error rate tracking
        with patch('voicecore.services.openai_service.OpenAIService') as mock_openai:
            
            call_count = 0
            
            async def mock_failing_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count <= 2:
                    raise Exception("Service error")
                
                return {"success": True, "response": "OK"}
            
            mock_openai.return_value.process_conversation.side_effect = mock_failing_call
            
            # Make calls that fail then succeed
            for i in range(3):
                try:
                    with monitoring_service.monitor_service_call("openai", "process_conversation"):
                        await mock_openai.return_value.process_conversation({})
                except Exception:
                    pass  # Expected failures
            
            # Get error metrics
            metrics = await monitoring_service.get_service_metrics("openai")
            
            assert metrics["total_calls"] == 3
            assert metrics["error_rate"] == 66.67  # 2 out of 3 failed
            assert metrics["success_rate"] == 33.33
    
    @pytest.mark.asyncio
    async def test_service_alerting(self, test_tenant):
        """Test service alerting based on metrics."""
        
        from voicecore.services.alerting_service import AlertingService
        
        alerting_service = AlertingService()
        
        # Mock high error rate scenario
        service_metrics = {
            "service": "twilio",
            "error_rate": 75.0,  # High error rate
            "average_response_time": 2000,  # Slow response
            "total_calls": 100,
            "timestamp": datetime.utcnow()
        }
        
        alerts = await alerting_service.check_service_alerts(service_metrics)
        
        # Should trigger alerts for high error rate and slow response
        assert len(alerts) >= 2
        
        error_rate_alert = next(
            (alert for alert in alerts if alert["type"] == "high_error_rate"),
            None
        )
        assert error_rate_alert is not None
        assert error_rate_alert["severity"] == "critical"
        
        slow_response_alert = next(
            (alert for alert in alerts if alert["type"] == "slow_response"),
            None
        )
        assert slow_response_alert is not None
        assert slow_response_alert["severity"] == "warning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])