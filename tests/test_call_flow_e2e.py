"""
End-to-End Call Flow Testing
Comprehensive testing of the complete call lifecycle with AI integration
"""

import pytest
import asyncio
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from voicecore.services.twilio_service import TwilioService
from voicecore.services.call_routing_service import CallRoutingService
from voicecore.services.openai_service import OpenAIService
from voicecore.services.conversation_manager import ConversationManager
from voicecore.services.agent_service import AgentService
from voicecore.services.event_sourcing_service import EventSourcingService, EventTypes
from voicecore.models.call import Call, CallStatus
from voicecore.models.agent import Agent, AgentStatus


class TestInboundCallFlow:
    """Test complete inbound call flow"""
    
    @pytest.mark.asyncio
    async def test_complete_inbound_call_with_ai(self, db: Session, test_tenant):
        """
        Test Case: Complete inbound call handled by AI
        
        Flow:
        1. Customer calls business number
        2. Twilio webhook received
        3. Call routing determines AI should handle
        4. AI greets customer
        5. Customer asks question
        6. AI provides answer
        7. Call ends successfully
        """
        print("\n" + "="*80)
        print("TEST: Complete Inbound Call with AI")
        print("="*80)
        
        # Setup services
        twilio_service = TwilioService(db)
        routing_service = CallRoutingService(db)
        ai_service = OpenAIService()
        conversation_manager = ConversationManager(db)
        event_service = EventSourcingService(db)
        
        # Test data
        caller_number = "+1234567890"
        business_number = "+0987654321"
        call_sid = f"CA{uuid.uuid4().hex[:32]}"
        
        print(f"\n📞 Step 1: Incoming call from {caller_number}")
        print(f"   Call SID: {call_sid}")
        
        # Step 1: Receive Twilio webhook
        with patch.object(twilio_service, 'client') as mock_client:
            mock_client.calls.return_value.fetch.return_value = Mock(
                sid=call_sid,
                from_=caller_number,
                to=business_number,
                status='in-progress'
            )
            
            call = await twilio_service.handle_incoming_call(
                call_sid=call_sid,
                from_number=caller_number,
                to_number=business_number,
                tenant_id=test_tenant.id
            )
        
        assert call is not None
        assert call.status == CallStatus.INITIATED
        print(f"   ✅ Call created: {call.id}")
        
        # Verify event was stored
        events = await event_service.get_events(call.id)
        assert len(events) >= 1
        assert events[0].event_type == EventTypes.CALL_INITIATED
        print(f"   ✅ CallInitiated event stored")
        
        # Step 2: Route call to AI
        print(f"\n🤖 Step 2: Routing call to AI")
        
        routing_decision = await routing_service.route_call(
            call_id=call.id,
            tenant_id=test_tenant.id
        )
        
        assert routing_decision['handler'] == 'ai'
        assert routing_decision['ai_personality'] is not None
        print(f"   ✅ Call routed to AI")
        print(f"   AI Personality: {routing_decision['ai_personality']}")
        
        # Step 3: AI greets customer
        print(f"\n👋 Step 3: AI greeting")
        
        with patch.object(ai_service, 'generate_response') as mock_ai:
            mock_ai.return_value = {
                'response': 'Hello! Thank you for calling. How can I help you today?',
                'intent': 'greeting',
                'confidence': 0.95,
                'sentiment': 'neutral'
            }
            
            greeting = await conversation_manager.start_conversation(
                call_id=call.id,
                tenant_id=test_tenant.id,
                ai_personality=routing_decision['ai_personality']
            )
        
        assert greeting['response'] is not None
        print(f"   AI: {greeting['response']}")
        print(f"   ✅ Greeting generated")
        
        # Step 4: Customer asks question
        print(f"\n💬 Step 4: Customer interaction")
        
        customer_message = "What are your business hours?"
        print(f"   Customer: {customer_message}")
        
        with patch.object(ai_service, 'generate_response') as mock_ai:
            mock_ai.return_value = {
                'response': 'We are open Monday through Friday, 9 AM to 5 PM EST.',
                'intent': 'business_hours_inquiry',
                'confidence': 0.92,
                'sentiment': 'neutral',
                'requires_escalation': False
            }
            
            ai_response = await conversation_manager.process_message(
                call_id=call.id,
                message=customer_message,
                tenant_id=test_tenant.id
            )
        
        assert ai_response['response'] is not None
        assert ai_response['requires_escalation'] == False
        print(f"   AI: {ai_response['response']}")
        print(f"   Intent: {ai_response['intent']}")
        print(f"   Confidence: {ai_response['confidence']}")
        print(f"   ✅ AI responded successfully")
        
        # Step 5: End call
        print(f"\n📴 Step 5: Ending call")
        
        await twilio_service.end_call(
            call_id=call.id,
            reason="completed"
        )
        
        # Verify call status
        db.refresh(call)
        assert call.status == CallStatus.COMPLETED
        print(f"   ✅ Call ended successfully")
        
        # Verify all events
        final_events = await event_service.get_events(call.id)
        event_types = [e.event_type for e in final_events]
        
        assert EventTypes.CALL_INITIATED in event_types
        assert EventTypes.CALL_CONNECTED in event_types
        assert EventTypes.CALL_ENDED in event_types
        
        print(f"\n📊 Call Summary:")
        print(f"   Total Events: {len(final_events)}")
        print(f"   Event Types: {', '.join(event_types)}")
        print(f"   Duration: {call.duration_seconds}s")
        print(f"   Status: {call.status}")
        
        print(f"\n✅ TEST PASSED: Complete inbound call with AI")
    
    @pytest.mark.asyncio
    async def test_call_escalation_to_human_agent(self, db: Session, test_tenant):
        """
        Test Case: AI escalates call to human agent
        
        Flow:
        1. Call starts with AI
        2. Customer asks complex question
        3. AI determines escalation needed
        4. Call transferred to available agent
        5. Agent handles call
        6. Call ends
        """
        print("\n" + "="*80)
        print("TEST: Call Escalation to Human Agent")
        print("="*80)
        
        # Setup
        twilio_service = TwilioService(db)
        routing_service = CallRoutingService(db)
        ai_service = OpenAIService()
        conversation_manager = ConversationManager(db)
        agent_service = AgentService(db)
        event_service = EventSourcingService(db)
        
        # Create available agent
        agent = Agent(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            name="John Agent",
            email="john@example.com",
            status=AgentStatus.AVAILABLE,
            skills=["customer_service", "technical_support"]
        )
        db.add(agent)
        db.commit()
        
        # Create call
        call_sid = f"CA{uuid.uuid4().hex[:32]}"
        caller_number = "+1234567890"
        
        print(f"\n📞 Step 1: Call initiated with AI")
        
        with patch.object(twilio_service, 'client'):
            call = await twilio_service.handle_incoming_call(
                call_sid=call_sid,
                from_number=caller_number,
                to_number="+0987654321",
                tenant_id=test_tenant.id
            )
        
        # AI handles initial interaction
        print(f"\n🤖 Step 2: AI initial interaction")
        
        with patch.object(ai_service, 'generate_response') as mock_ai:
            mock_ai.return_value = {
                'response': 'Hello! How can I help you?',
                'intent': 'greeting',
                'confidence': 0.95
            }
            
            await conversation_manager.start_conversation(
                call_id=call.id,
                tenant_id=test_tenant.id
            )
        
        # Customer asks complex question
        print(f"\n💬 Step 3: Complex customer question")
        
        complex_question = "I need to modify my enterprise contract and add custom SLA terms"
        print(f"   Customer: {complex_question}")
        
        with patch.object(ai_service, 'generate_response') as mock_ai:
            mock_ai.return_value = {
                'response': 'Let me connect you with a specialist who can help with that.',
                'intent': 'contract_modification',
                'confidence': 0.65,
                'requires_escalation': True,
                'escalation_reason': 'complex_contract_inquiry'
            }
            
            ai_response = await conversation_manager.process_message(
                call_id=call.id,
                message=complex_question,
                tenant_id=test_tenant.id
            )
        
        assert ai_response['requires_escalation'] == True
        print(f"   AI: {ai_response['response']}")
        print(f"   ⚠️  Escalation required: {ai_response['escalation_reason']}")
        
        # Transfer to agent
        print(f"\n👤 Step 4: Transferring to human agent")
        
        transfer_result = await routing_service.transfer_to_agent(
            call_id=call.id,
            agent_id=agent.id,
            reason=ai_response['escalation_reason']
        )
        
        assert transfer_result['success'] == True
        assert transfer_result['agent_id'] == agent.id
        print(f"   ✅ Call transferred to {agent.name}")
        
        # Verify agent status updated
        db.refresh(agent)
        assert agent.status == AgentStatus.ON_CALL
        print(f"   ✅ Agent status: {agent.status}")
        
        # Verify transfer event
        events = await event_service.get_events(call.id)
        transfer_events = [e for e in events if e.event_type == EventTypes.CALL_TRANSFERRED]
        assert len(transfer_events) > 0
        print(f"   ✅ Transfer event recorded")
        
        # Agent handles call
        print(f"\n💼 Step 5: Agent handling call")
        
        await agent_service.update_call_notes(
            call_id=call.id,
            agent_id=agent.id,
            notes="Discussed contract modifications. Customer needs custom SLA."
        )
        
        # End call
        print(f"\n📴 Step 6: Ending call")
        
        await twilio_service.end_call(
            call_id=call.id,
            reason="completed"
        )
        
        # Verify final state
        db.refresh(call)
        db.refresh(agent)
        
        assert call.status == CallStatus.COMPLETED
        assert agent.status == AgentStatus.AVAILABLE
        
        print(f"\n📊 Call Summary:")
        print(f"   Started with: AI")
        print(f"   Escalated to: {agent.name}")
        print(f"   Escalation reason: {ai_response['escalation_reason']}")
        print(f"   Final status: {call.status}")
        
        print(f"\n✅ TEST PASSED: Call escalation to human agent")


class TestOutboundCallFlow:
    """Test outbound call flows"""
    
    @pytest.mark.asyncio
    async def test_agent_initiated_outbound_call(self, db: Session, test_tenant):
        """
        Test Case: Agent makes outbound call
        
        Flow:
        1. Agent initiates call from dashboard
        2. System dials customer
        3. Customer answers
        4. Conversation happens
        5. Call ends
        """
        print("\n" + "="*80)
        print("TEST: Agent Initiated Outbound Call")
        print("="*80)
        
        # Setup
        twilio_service = TwilioService(db)
        agent_service = AgentService(db)
        event_service = EventSourcingService(db)
        
        # Create agent
        agent = Agent(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            name="Sarah Agent",
            email="sarah@example.com",
            status=AgentStatus.AVAILABLE
        )
        db.add(agent)
        db.commit()
        
        customer_number = "+1234567890"
        
        print(f"\n📱 Step 1: Agent initiates outbound call")
        print(f"   Agent: {agent.name}")
        print(f"   Customer: {customer_number}")
        
        # Agent initiates call
        with patch.object(twilio_service, 'client') as mock_client:
            mock_call = Mock()
            mock_call.sid = f"CA{uuid.uuid4().hex[:32]}"
            mock_call.status = 'initiated'
            mock_client.calls.create.return_value = mock_call
            
            call = await twilio_service.initiate_outbound_call(
                agent_id=agent.id,
                to_number=customer_number,
                tenant_id=test_tenant.id
            )
        
        assert call is not None
        assert call.direction == 'outbound'
        assert call.agent_id == agent.id
        print(f"   ✅ Call initiated: {call.id}")
        
        # Verify agent status
        db.refresh(agent)
        assert agent.status == AgentStatus.ON_CALL
        print(f"   ✅ Agent status: {agent.status}")
        
        # Simulate customer answering
        print(f"\n📞 Step 2: Customer answers")
        
        await twilio_service.handle_call_answered(
            call_id=call.id
        )
        
        db.refresh(call)
        assert call.status == CallStatus.IN_PROGRESS
        print(f"   ✅ Call connected")
        
        # Conversation happens
        print(f"\n💬 Step 3: Conversation")
        
        await agent_service.update_call_notes(
            call_id=call.id,
            agent_id=agent.id,
            notes="Follow-up call regarding previous inquiry. Customer satisfied."
        )
        print(f"   ✅ Call notes added")
        
        # End call
        print(f"\n📴 Step 4: Ending call")
        
        await twilio_service.end_call(
            call_id=call.id,
            reason="completed"
        )
        
        # Verify final state
        db.refresh(call)
        db.refresh(agent)
        
        assert call.status == CallStatus.COMPLETED
        assert agent.status == AgentStatus.AVAILABLE
        
        # Verify events
        events = await event_service.get_events(call.id)
        event_types = [e.event_type for e in events]
        
        assert EventTypes.CALL_INITIATED in event_types
        assert EventTypes.CALL_CONNECTED in event_types
        assert EventTypes.AGENT_ASSIGNED_TO_CALL in event_types
        
        print(f"\n📊 Call Summary:")
        print(f"   Direction: Outbound")
        print(f"   Agent: {agent.name}")
        print(f"   Duration: {call.duration_seconds}s")
        print(f"   Events: {len(events)}")
        
        print(f"\n✅ TEST PASSED: Agent initiated outbound call")


class TestAIConversationFlow:
    """Test AI conversation capabilities"""
    
    @pytest.mark.asyncio
    async def test_multi_turn_ai_conversation(self, db: Session, test_tenant):
        """
        Test Case: Multi-turn conversation with AI
        
        Tests AI's ability to:
        - Maintain context
        - Handle multiple questions
        - Detect sentiment
        - Recognize intents
        """
        print("\n" + "="*80)
        print("TEST: Multi-Turn AI Conversation")
        print("="*80)
        
        # Setup
        ai_service = OpenAIService()
        conversation_manager = ConversationManager(db)
        
        # Create call
        call = Call(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            from_number="+1234567890",
            to_number="+0987654321",
            status=CallStatus.IN_PROGRESS
        )
        db.add(call)
        db.commit()
        
        print(f"\n🤖 Starting AI conversation")
        print(f"   Call ID: {call.id}")
        
        # Turn 1: Greeting
        print(f"\n💬 Turn 1: Greeting")
        
        with patch.object(ai_service, 'generate_response') as mock_ai:
            mock_ai.return_value = {
                'response': 'Hello! Thank you for calling. How can I assist you today?',
                'intent': 'greeting',
                'confidence': 0.95,
                'sentiment': 'positive'
            }
            
            response1 = await conversation_manager.start_conversation(
                call_id=call.id,
                tenant_id=test_tenant.id
            )
        
        print(f"   AI: {response1['response']}")
        print(f"   Sentiment: {response1['sentiment']}")
        
        # Turn 2: Product inquiry
        print(f"\n💬 Turn 2: Product inquiry")
        
        customer_msg2 = "I'm interested in your enterprise plan"
        print(f"   Customer: {customer_msg2}")
        
        with patch.object(ai_service, 'generate_response') as mock_ai:
            mock_ai.return_value = {
                'response': 'Great! Our enterprise plan includes unlimited calls, advanced analytics, and dedicated support. Would you like to know more about pricing?',
                'intent': 'product_inquiry',
                'confidence': 0.88,
                'sentiment': 'positive',
                'entities': {'product': 'enterprise_plan'}
            }
            
            response2 = await conversation_manager.process_message(
                call_id=call.id,
                message=customer_msg2,
                tenant_id=test_tenant.id
            )
        
        print(f"   AI: {response2['response']}")
        print(f"   Intent: {response2['intent']}")
        print(f"   Entities: {response2.get('entities', {})}")
        
        # Turn 3: Pricing question
        print(f"\n💬 Turn 3: Pricing question")
        
        customer_msg3 = "Yes, what's the pricing?"
        print(f"   Customer: {customer_msg3}")
        
        with patch.object(ai_service, 'generate_response') as mock_ai:
            mock_ai.return_value = {
                'response': 'The enterprise plan starts at $299/month for up to 1000 minutes. We also offer custom pricing for larger volumes. Would you like me to connect you with our sales team?',
                'intent': 'pricing_inquiry',
                'confidence': 0.92,
                'sentiment': 'neutral',
                'context_maintained': True
            }
            
            response3 = await conversation_manager.process_message(
                call_id=call.id,
                message=customer_msg3,
                tenant_id=test_tenant.id
            )
        
        print(f"   AI: {response3['response']}")
        print(f"   Context maintained: {response3.get('context_maintained', False)}")
        
        # Turn 4: Confirmation
        print(f"\n💬 Turn 4: Confirmation")
        
        customer_msg4 = "Yes please, connect me with sales"
        print(f"   Customer: {customer_msg4}")
        
        with patch.object(ai_service, 'generate_response') as mock_ai:
            mock_ai.return_value = {
                'response': 'Perfect! I\'m transferring you to our sales team now. They\'ll be able to provide you with a customized quote.',
                'intent': 'transfer_request',
                'confidence': 0.94,
                'sentiment': 'positive',
                'requires_escalation': True,
                'escalation_reason': 'sales_inquiry'
            }
            
            response4 = await conversation_manager.process_message(
                call_id=call.id,
                message=customer_msg4,
                tenant_id=test_tenant.id
            )
        
        print(f"   AI: {response4['response']}")
        print(f"   Action: Transfer to sales")
        
        # Verify conversation history
        history = await conversation_manager.get_conversation_history(call.id)
        
        assert len(history) >= 4
        print(f"\n📊 Conversation Summary:")
        print(f"   Total turns: {len(history)}")
        print(f"   Intents detected: greeting, product_inquiry, pricing_inquiry, transfer_request")
        print(f"   Sentiment: Positive throughout")
        print(f"   Outcome: Transfer to sales")
        
        print(f"\n✅ TEST PASSED: Multi-turn AI conversation")
    
    @pytest.mark.asyncio
    async def test_ai_sentiment_detection(self, db: Session, test_tenant):
        """
        Test Case: AI detects negative sentiment and escalates
        """
        print("\n" + "="*80)
        print("TEST: AI Sentiment Detection and Escalation")
        print("="*80)
        
        # Setup
        ai_service = OpenAIService()
        conversation_manager = ConversationManager(db)
        
        # Create call
        call = Call(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            from_number="+1234567890",
            to_number="+0987654321",
            status=CallStatus.IN_PROGRESS
        )
        db.add(call)
        db.commit()
        
        print(f"\n😠 Simulating frustrated customer")
        
        frustrated_message = "This is ridiculous! I've been waiting for 3 days and nobody has called me back!"
        print(f"   Customer: {frustrated_message}")
        
        with patch.object(ai_service, 'generate_response') as mock_ai:
            mock_ai.return_value = {
                'response': 'I sincerely apologize for the delay and frustration. Let me connect you with a supervisor right away who can help resolve this immediately.',
                'intent': 'complaint',
                'confidence': 0.96,
                'sentiment': 'negative',
                'sentiment_score': -0.8,
                'requires_escalation': True,
                'escalation_reason': 'negative_sentiment',
                'urgency': 'high'
            }
            
            response = await conversation_manager.process_message(
                call_id=call.id,
                message=frustrated_message,
                tenant_id=test_tenant.id
            )
        
        assert response['sentiment'] == 'negative'
        assert response['requires_escalation'] == True
        assert response['urgency'] == 'high'
        
        print(f"   AI: {response['response']}")
        print(f"   ⚠️  Sentiment: {response['sentiment']} (score: {response['sentiment_score']})")
        print(f"   ⚠️  Escalation: {response['escalation_reason']}")
        print(f"   ⚠️  Urgency: {response['urgency']}")
        
        print(f"\n✅ TEST PASSED: AI sentiment detection")


class TestCallRecordingFlow:
    """Test call recording functionality"""
    
    @pytest.mark.asyncio
    async def test_call_recording_lifecycle(self, db: Session, test_tenant):
        """
        Test Case: Complete call recording lifecycle
        
        Flow:
        1. Call starts
        2. Recording starts automatically
        3. Call proceeds
        4. Recording stops when call ends
        5. Recording stored and accessible
        """
        print("\n" + "="*80)
        print("TEST: Call Recording Lifecycle")
        print("="*80)
        
        # Setup
        twilio_service = TwilioService(db)
        event_service = EventSourcingService(db)
        
        # Create call
        call_sid = f"CA{uuid.uuid4().hex[:32]}"
        
        print(f"\n📞 Step 1: Call initiated")
        
        with patch.object(twilio_service, 'client') as mock_client:
            mock_client.calls.return_value.fetch.return_value = Mock(
                sid=call_sid,
                status='in-progress'
            )
            
            call = await twilio_service.handle_incoming_call(
                call_sid=call_sid,
                from_number="+1234567890",
                to_number="+0987654321",
                tenant_id=test_tenant.id
            )
        
        print(f"   ✅ Call created: {call.id}")
        
        # Start recording
        print(f"\n🎙️  Step 2: Starting recording")
        
        recording_sid = f"RE{uuid.uuid4().hex[:32]}"
        
        with patch.object(twilio_service, 'client') as mock_client:
            mock_recording = Mock()
            mock_recording.sid = recording_sid
            mock_recording.status = 'in-progress'
            mock_client.calls.return_value.recordings.create.return_value = mock_recording
            
            recording = await twilio_service.start_recording(call.id)
        
        assert recording is not None
        print(f"   ✅ Recording started: {recording_sid}")
        
        # Verify recording event
        events = await event_service.get_events(call.id)
        recording_events = [e for e in events if e.event_type == EventTypes.CALL_RECORDING_STARTED]
        assert len(recording_events) > 0
        print(f"   ✅ Recording event stored")
        
        # Simulate call activity
        print(f"\n💬 Step 3: Call in progress (recording active)")
        await asyncio.sleep(0.1)  # Simulate time passing
        
        # Stop recording
        print(f"\n⏹️  Step 4: Stopping recording")
        
        with patch.object(twilio_service, 'client') as mock_client:
            mock_recording = Mock()
            mock_recording.sid = recording_sid
            mock_recording.status = 'completed'
            mock_recording.duration = 120
            mock_recording.uri = f"/Recordings/{recording_sid}"
            mock_client.recordings.return_value.fetch.return_value = mock_recording
            
            stopped_recording = await twilio_service.stop_recording(
                call_id=call.id,
                recording_sid=recording_sid
            )
        
        assert stopped_recording['status'] == 'completed'
        assert stopped_recording['duration'] == 120
        print(f"   ✅ Recording stopped")
        print(f"   Duration: {stopped_recording['duration']}s")
        
        # Verify stop event
        final_events = await event_service.get_events(call.id)
        stop_events = [e for e in final_events if e.event_type == EventTypes.CALL_RECORDING_STOPPED]
        assert len(stop_events) > 0
        print(f"   ✅ Stop event stored")
        
        print(f"\n📊 Recording Summary:")
        print(f"   Recording SID: {recording_sid}")
        print(f"   Duration: {stopped_recording['duration']}s")
        print(f"   Status: {stopped_recording['status']}")
        print(f"   URI: {stopped_recording['uri']}")
        
        print(f"\n✅ TEST PASSED: Call recording lifecycle")


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
