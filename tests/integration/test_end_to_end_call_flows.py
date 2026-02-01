"""
Integration tests for end-to-end call flows.

Tests complete call scenarios from incoming call to resolution,
including AI interactions, transfers, and call logging.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from voicecore.main import app
from voicecore.database import get_db_session
from voicecore.models.tenant import Tenant
from voicecore.models.agent import Agent, AgentStatus
from voicecore.models.call import Call, CallStatus
from voicecore.services.tenant_service import TenantService
from voicecore.services.agent_service import AgentService
from voicecore.services.call_routing_service import CallRoutingService
from voicecore.services.twilio_service import TwilioService
from voicecore.services.openai_service import OpenAIService
from voicecore.services.call_logging_service import CallLoggingService


@pytest.fixture
async def test_tenant(db_session: AsyncSession):
    """Create a test tenant for integration tests."""
    tenant_service = TenantService()
    
    tenant_data = {
        "company_name": "Test Company E2E",
        "domain": "test-e2e.com",
        "phone_number": "+1234567890",
        "ai_name": "Sofia",
        "ai_voice": "alloy",
        "business_hours_start": "09:00",
        "business_hours_end": "17:00",
        "timezone": "UTC"
    }
    
    tenant = await tenant_service.create_tenant(tenant_data)
    yield tenant
    
    # Cleanup
    await tenant_service.delete_tenant(tenant.id)


@pytest.fixture
async def test_agents(db_session: AsyncSession, test_tenant):
    """Create test agents for integration tests."""
    agent_service = AgentService()
    
    agents = []
    
    # Create customer service agent
    agent1_data = {
        "name": "John Doe",
        "email": "john@test-e2e.com",
        "extension": "101",
        "department": "customer_service",
        "status": AgentStatus.AVAILABLE,
        "tenant_id": test_tenant.id
    }
    agent1 = await agent_service.create_agent(agent1_data)
    agents.append(agent1)
    
    # Create sales agent
    agent2_data = {
        "name": "Jane Smith",
        "email": "jane@test-e2e.com",
        "extension": "102",
        "department": "sales",
        "status": AgentStatus.AVAILABLE,
        "tenant_id": test_tenant.id
    }
    agent2 = await agent_service.create_agent(agent2_data)
    agents.append(agent2)
    
    yield agents
    
    # Cleanup
    for agent in agents:
        await agent_service.delete_agent(agent.id)


@pytest.fixture
def mock_external_services():
    """Mock external services for integration tests."""
    with patch('voicecore.services.twilio_service.TwilioService') as mock_twilio, \
         patch('voicecore.services.openai_service.OpenAIService') as mock_openai:
        
        # Mock Twilio service
        mock_twilio_instance = AsyncMock()
        mock_twilio.return_value = mock_twilio_instance
        mock_twilio_instance.create_call.return_value = {
            "sid": "CA123456789",
            "status": "in-progress"
        }
        mock_twilio_instance.transfer_call.return_value = True
        mock_twilio_instance.end_call.return_value = True
        
        # Mock OpenAI service
        mock_openai_instance = AsyncMock()
        mock_openai.return_value = mock_openai_instance
        mock_openai_instance.process_conversation.return_value = {
            "response": "Hello! How can I help you today?",
            "action": "continue",
            "confidence": 0.95
        }
        mock_openai_instance.analyze_intent.return_value = {
            "intent": "customer_service",
            "confidence": 0.9,
            "entities": {}
        }
        
        yield {
            "twilio": mock_twilio_instance,
            "openai": mock_openai_instance
        }


class TestEndToEndCallFlows:
    """Test complete call flow scenarios."""
    
    @pytest.mark.asyncio
    async def test_successful_customer_service_call_flow(
        self,
        db_session: AsyncSession,
        test_tenant,
        test_agents,
        mock_external_services
    ):
        """Test complete customer service call flow from start to finish."""
        
        # Setup
        call_routing_service = CallRoutingService()
        call_logging_service = CallLoggingService()
        
        # Simulate incoming call
        call_data = {
            "from_number": "+1987654321",
            "to_number": test_tenant.phone_number,
            "twilio_call_sid": "CA123456789",
            "tenant_id": test_tenant.id
        }
        
        # Step 1: Incoming call received
        call = await call_routing_service.handle_incoming_call(call_data)
        
        assert call is not None
        assert call.tenant_id == test_tenant.id
        assert call.from_number == "+1987654321"
        assert call.status == CallStatus.IN_PROGRESS
        
        # Step 2: AI processes initial interaction
        conversation_data = {
            "call_id": call.id,
            "message": "Hi, I need help with my account",
            "timestamp": datetime.utcnow()
        }
        
        ai_response = await call_routing_service.process_ai_interaction(
            call.id, conversation_data
        )
        
        assert ai_response["action"] == "continue"
        assert "help" in ai_response["response"].lower()
        
        # Step 3: AI determines transfer is needed
        transfer_request = {
            "call_id": call.id,
            "department": "customer_service",
            "reason": "Account assistance needed"
        }
        
        transfer_result = await call_routing_service.transfer_call(
            call.id, transfer_request
        )
        
        assert transfer_result["success"] is True
        assert transfer_result["agent_id"] is not None
        
        # Step 4: Agent accepts call
        agent_id = transfer_result["agent_id"]
        accept_result = await call_routing_service.agent_accept_call(
            call.id, agent_id
        )
        
        assert accept_result is True
        
        # Step 5: Call conversation continues
        agent_conversation = {
            "call_id": call.id,
            "agent_id": agent_id,
            "message": "Hello, I understand you need help with your account. How can I assist you?",
            "timestamp": datetime.utcnow()
        }
        
        await call_logging_service.log_conversation(agent_conversation)
        
        # Step 6: Call is completed successfully
        completion_data = {
            "call_id": call.id,
            "resolution": "Account issue resolved",
            "satisfaction_rating": 5,
            "notes": "Customer was satisfied with the service"
        }
        
        end_result = await call_routing_service.end_call(call.id, completion_data)
        
        assert end_result is True
        
        # Verify call was logged properly
        call_log = await call_logging_service.get_call_details(call.id)
        
        assert call_log is not None
        assert call_log["status"] == "completed"
        assert call_log["resolution"] == "Account issue resolved"
        assert len(call_log["conversation_log"]) > 0
    
    @pytest.mark.asyncio
    async def test_call_flow_with_multiple_transfers(
        self,
        db_session: AsyncSession,
        test_tenant,
        test_agents,
        mock_external_services
    ):
        """Test call flow with multiple department transfers."""
        
        call_routing_service = CallRoutingService()
        
        # Incoming call
        call_data = {
            "from_number": "+1555123456",
            "to_number": test_tenant.phone_number,
            "twilio_call_sid": "CA987654321",
            "tenant_id": test_tenant.id
        }
        
        call = await call_routing_service.handle_incoming_call(call_data)
        
        # First transfer to sales
        transfer1 = await call_routing_service.transfer_call(
            call.id, {"department": "sales", "reason": "Product inquiry"}
        )
        
        assert transfer1["success"] is True
        sales_agent_id = transfer1["agent_id"]
        
        # Sales agent realizes it's a support issue
        transfer2 = await call_routing_service.transfer_call(
            call.id, {
                "department": "customer_service",
                "reason": "Technical support needed",
                "from_agent_id": sales_agent_id
            }
        )
        
        assert transfer2["success"] is True
        support_agent_id = transfer2["agent_id"]
        assert support_agent_id != sales_agent_id
        
        # Support agent accepts and resolves
        await call_routing_service.agent_accept_call(call.id, support_agent_id)
        
        end_result = await call_routing_service.end_call(
            call.id, {"resolution": "Technical issue resolved"}
        )
        
        assert end_result is True
    
    @pytest.mark.asyncio
    async def test_call_flow_with_ai_resolution(
        self,
        db_session: AsyncSession,
        test_tenant,
        test_agents,
        mock_external_services
    ):
        """Test call flow where AI resolves the issue without transfer."""
        
        # Mock AI to provide resolution
        mock_external_services["openai"].process_conversation.return_value = {
            "response": "I've found your account and updated your information. Is there anything else I can help you with?",
            "action": "resolve",
            "confidence": 0.98,
            "resolution": "Account information updated"
        }
        
        call_routing_service = CallRoutingService()
        
        # Incoming call
        call_data = {
            "from_number": "+1444555666",
            "to_number": test_tenant.phone_number,
            "twilio_call_sid": "CA111222333",
            "tenant_id": test_tenant.id
        }
        
        call = await call_routing_service.handle_incoming_call(call_data)
        
        # AI interaction that resolves the issue
        conversation_data = {
            "call_id": call.id,
            "message": "I need to update my phone number",
            "timestamp": datetime.utcnow()
        }
        
        ai_response = await call_routing_service.process_ai_interaction(
            call.id, conversation_data
        )
        
        assert ai_response["action"] == "resolve"
        assert "updated" in ai_response["response"].lower()
        
        # Call ends with AI resolution
        end_result = await call_routing_service.end_call(
            call.id, {"resolution": ai_response["resolution"], "resolved_by": "ai"}
        )
        
        assert end_result is True
    
    @pytest.mark.asyncio
    async def test_call_flow_with_voicemail(
        self,
        db_session: AsyncSession,
        test_tenant,
        test_agents,
        mock_external_services
    ):
        """Test call flow that goes to voicemail when no agents available."""
        
        # Set all agents to busy
        agent_service = AgentService()
        for agent in test_agents:
            await agent_service.update_agent_status(
                agent.id, AgentStatus.BUSY
            )
        
        call_routing_service = CallRoutingService()
        
        # Incoming call
        call_data = {
            "from_number": "+1777888999",
            "to_number": test_tenant.phone_number,
            "twilio_call_sid": "CA444555666",
            "tenant_id": test_tenant.id
        }
        
        call = await call_routing_service.handle_incoming_call(call_data)
        
        # Attempt transfer when no agents available
        transfer_result = await call_routing_service.transfer_call(
            call.id, {"department": "customer_service"}
        )
        
        # Should route to voicemail
        assert transfer_result["success"] is False
        assert transfer_result["action"] == "voicemail"
        
        # Simulate voicemail recording
        voicemail_data = {
            "call_id": call.id,
            "recording_url": "https://recordings.twilio.com/test123",
            "duration": 45,
            "transcript": "Hi, this is John. Please call me back at 555-1234."
        }
        
        voicemail_result = await call_routing_service.handle_voicemail(
            call.id, voicemail_data
        )
        
        assert voicemail_result is True
    
    @pytest.mark.asyncio
    async def test_call_flow_with_spam_detection(
        self,
        db_session: AsyncSession,
        test_tenant,
        test_agents,
        mock_external_services
    ):
        """Test call flow with spam detection and blocking."""
        
        call_routing_service = CallRoutingService()
        
        # Incoming call from known spam number
        call_data = {
            "from_number": "+1000000000",  # Suspicious number
            "to_number": test_tenant.phone_number,
            "twilio_call_sid": "CA000111222",
            "tenant_id": test_tenant.id
        }
        
        # Mock spam detection
        with patch('voicecore.services.spam_detection_service.SpamDetectionService') as mock_spam:
            mock_spam_instance = AsyncMock()
            mock_spam.return_value = mock_spam_instance
            mock_spam_instance.analyze_call.return_value = {
                "is_spam": True,
                "confidence": 0.95,
                "reasons": ["suspicious_number", "robocall_pattern"],
                "action": "block"
            }
            
            call = await call_routing_service.handle_incoming_call(call_data)
            
            # Call should be blocked
            assert call.status == CallStatus.BLOCKED
            
            # Verify spam was logged
            call_log = await call_routing_service.get_call_log(call.id)
            assert call_log["spam_detected"] is True
            assert call_log["spam_confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_call_flow_error_handling(
        self,
        db_session: AsyncSession,
        test_tenant,
        test_agents,
        mock_external_services
    ):
        """Test call flow error handling and recovery."""
        
        call_routing_service = CallRoutingService()
        
        # Incoming call
        call_data = {
            "from_number": "+1333444555",
            "to_number": test_tenant.phone_number,
            "twilio_call_sid": "CA777888999",
            "tenant_id": test_tenant.id
        }
        
        call = await call_routing_service.handle_incoming_call(call_data)
        
        # Simulate AI service failure
        mock_external_services["openai"].process_conversation.side_effect = Exception("AI service unavailable")
        
        # AI interaction should handle error gracefully
        conversation_data = {
            "call_id": call.id,
            "message": "Hello, I need help",
            "timestamp": datetime.utcnow()
        }
        
        ai_response = await call_routing_service.process_ai_interaction(
            call.id, conversation_data
        )
        
        # Should fallback to human transfer
        assert ai_response["action"] == "transfer"
        assert "technical difficulties" in ai_response["response"].lower()
        
        # Transfer should still work
        transfer_result = await call_routing_service.transfer_call(
            call.id, {"department": "customer_service", "reason": "AI service failure"}
        )
        
        assert transfer_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_call_handling(
        self,
        db_session: AsyncSession,
        test_tenant,
        test_agents,
        mock_external_services
    ):
        """Test handling multiple concurrent calls."""
        
        call_routing_service = CallRoutingService()
        
        # Create multiple concurrent calls
        call_tasks = []
        
        for i in range(5):
            call_data = {
                "from_number": f"+155512340{i}",
                "to_number": test_tenant.phone_number,
                "twilio_call_sid": f"CA12345678{i}",
                "tenant_id": test_tenant.id
            }
            
            task = asyncio.create_task(
                call_routing_service.handle_incoming_call(call_data)
            )
            call_tasks.append(task)
        
        # Wait for all calls to be processed
        calls = await asyncio.gather(*call_tasks)
        
        # Verify all calls were created successfully
        assert len(calls) == 5
        for call in calls:
            assert call is not None
            assert call.tenant_id == test_tenant.id
            assert call.status in [CallStatus.IN_PROGRESS, CallStatus.QUEUED]
        
        # Verify calls have unique IDs
        call_ids = [call.id for call in calls]
        assert len(set(call_ids)) == 5
    
    @pytest.mark.asyncio
    async def test_call_flow_with_recording_and_transcription(
        self,
        db_session: AsyncSession,
        test_tenant,
        test_agents,
        mock_external_services
    ):
        """Test call flow with recording and transcription enabled."""
        
        call_routing_service = CallRoutingService()
        call_logging_service = CallLoggingService()
        
        # Incoming call
        call_data = {
            "from_number": "+1666777888",
            "to_number": test_tenant.phone_number,
            "twilio_call_sid": "CA555666777",
            "tenant_id": test_tenant.id,
            "recording_enabled": True,
            "transcription_enabled": True
        }
        
        call = await call_routing_service.handle_incoming_call(call_data)
        
        # Process AI interaction with transcription
        conversation_data = {
            "call_id": call.id,
            "message": "I need to cancel my subscription",
            "audio_url": "https://recordings.twilio.com/audio123",
            "timestamp": datetime.utcnow()
        }
        
        ai_response = await call_routing_service.process_ai_interaction(
            call.id, conversation_data
        )
        
        # Transfer to appropriate department
        transfer_result = await call_routing_service.transfer_call(
            call.id, {"department": "customer_service"}
        )
        
        agent_id = transfer_result["agent_id"]
        await call_routing_service.agent_accept_call(call.id, agent_id)
        
        # End call with recording
        completion_data = {
            "call_id": call.id,
            "resolution": "Subscription cancelled",
            "recording_url": "https://recordings.twilio.com/full_call_123",
            "transcript": "Full conversation transcript here...",
            "duration": 180
        }
        
        end_result = await call_routing_service.end_call(call.id, completion_data)
        
        assert end_result is True
        
        # Verify recording and transcript were saved
        call_details = await call_logging_service.get_call_details(call.id)
        
        assert call_details["recording_url"] is not None
        assert call_details["transcript"] is not None
        assert call_details["duration"] == 180


@pytest.mark.asyncio
async def test_call_flow_performance_under_load(
    db_session: AsyncSession,
    test_tenant,
    test_agents,
    mock_external_services
):
    """Test system performance under high call volume."""
    
    call_routing_service = CallRoutingService()
    
    # Simulate high call volume
    start_time = datetime.utcnow()
    call_count = 50
    
    # Create concurrent calls
    call_tasks = []
    for i in range(call_count):
        call_data = {
            "from_number": f"+1{str(i).zfill(10)}",
            "to_number": test_tenant.phone_number,
            "twilio_call_sid": f"CA{str(i).zfill(9)}",
            "tenant_id": test_tenant.id
        }
        
        task = asyncio.create_task(
            call_routing_service.handle_incoming_call(call_data)
        )
        call_tasks.append(task)
    
    # Process all calls
    calls = await asyncio.gather(*call_tasks, return_exceptions=True)
    
    end_time = datetime.utcnow()
    processing_time = (end_time - start_time).total_seconds()
    
    # Verify performance metrics
    successful_calls = [c for c in calls if not isinstance(c, Exception)]
    
    assert len(successful_calls) >= call_count * 0.95  # 95% success rate
    assert processing_time < 30  # Should process 50 calls in under 30 seconds
    
    # Verify no duplicate call IDs
    call_ids = [call.id for call in successful_calls if hasattr(call, 'id')]
    assert len(set(call_ids)) == len(call_ids)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])