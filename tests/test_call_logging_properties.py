"""
Property-based tests for Call Logging functionality in VoiceCore AI.

Tests Property 11: Call Activity Logging and Property 21: Automatic Transcription
to validate comprehensive call logging, recording management, and transcript generation.
"""

import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant

from voicecore.services.call_logging_service import (
    CallLoggingService,
    EventType,
    LogLevel,
    CallLogEntry,
    RecordingInfo,
    TranscriptInfo,
    CallLoggingServiceError,
    RecordingError,
    TranscriptionError
)
from voicecore.models import Call, CallStatus, CallDirection, CallType
from tests.conftest import create_test_call, create_test_agent


# Test data generators
@st.composite
def generate_event_type(draw):
    """Generate valid event type."""
    return draw(st.sampled_from(list(EventType)))


@st.composite
def generate_log_level(draw):
    """Generate valid log level."""
    return draw(st.sampled_from(list(LogLevel)))


@st.composite
def generate_call_metadata(draw):
    """Generate realistic call metadata."""
    return draw(st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(
            st.text(min_size=1, max_size=50),
            st.integers(min_value=0, max_value=10000),
            st.floats(min_value=0.0, max_value=100.0),
            st.booleans()
        ),
        max_size=10
    ))


@st.composite
def generate_phone_number(draw):
    """Generate valid phone number."""
    return f"+1{draw(st.integers(min_value=1000000000, max_value=9999999999))}"


@st.composite
def generate_recording_info(draw):
    """Generate realistic recording information."""
    return RecordingInfo(
        recording_sid=f"RE{draw(st.text(alphabet='0123456789abcdef', min_size=32, max_size=32))}",
        recording_url=f"https://api.twilio.com/recordings/{draw(st.text(min_size=10, max_size=20))}.mp3",
        duration=draw(st.integers(min_value=1, max_value=3600)),
        file_size=draw(st.integers(min_value=1000, max_value=50000000)),
        format=draw(st.sampled_from(["mp3", "wav"])),
        status=draw(st.sampled_from(["in-progress", "completed", "failed"])),
        created_at=datetime.utcnow()
    )


@st.composite
def generate_transcript_text(draw):
    """Generate realistic transcript text."""
    sentences = [
        "Hello, thank you for calling our company.",
        "How can I help you today?",
        "I understand your concern about the billing issue.",
        "Let me transfer you to our billing department.",
        "Please hold while I look up your account information.",
        "Thank you for your patience.",
        "Is there anything else I can help you with?",
        "Have a great day and thank you for calling."
    ]
    
    num_sentences = draw(st.integers(min_value=1, max_value=len(sentences)))
    selected_sentences = draw(st.lists(
        st.sampled_from(sentences), 
        min_size=num_sentences, 
        max_size=num_sentences,
        unique=True
    ))
    
    return " ".join(selected_sentences)


@st.composite
def generate_transcript_info(draw):
    """Generate realistic transcript information."""
    transcript_text = draw(generate_transcript_text())
    
    return TranscriptInfo(
        transcript_text=transcript_text,
        confidence_score=draw(st.floats(min_value=0.7, max_value=1.0)),
        language=draw(st.sampled_from(["en", "es", "fr", "de"])),
        word_count=len(transcript_text.split()),
        processing_time_ms=draw(st.integers(min_value=1000, max_value=30000)),
        created_at=datetime.utcnow(),
        segments=draw(st.lists(
            st.dictionaries(
                st.text(min_size=1, max_size=10),
                st.one_of(st.text(min_size=1, max_size=50), st.floats(min_value=0.0, max_value=100.0)),
                max_size=5
            ),
            max_size=10
        ))
    )


class TestCallLoggingProperties:
    """Property-based tests for Call Logging Service."""
    
    @pytest.fixture
    def call_logging_service(self):
        """Create call logging service instance."""
        return CallLoggingService()
    
    @given(
        call_id=st.uuids(),
        tenant_id=st.uuids(),
        event_type=generate_event_type(),
        message=st.text(min_size=1, max_size=200),
        level=generate_log_level(),
        metadata=generate_call_metadata(),
        agent_id=st.one_of(st.none(), st.uuids()),
        duration_ms=st.one_of(st.none(), st.integers(min_value=0, max_value=300000))
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_call_event_logging_consistency(
        self, call_logging_service, call_id, tenant_id, event_type, message, 
        level, metadata, agent_id, duration_ms
    ):
        """
        **Validates: Requirements 4.6, 8.4**
        
        Property 11: Call Activity Logging
        All call events must be logged consistently with proper metadata and timestamps.
        """
        with patch('voicecore.services.call_logging_service.get_db_session') as mock_db, \
             patch('voicecore.services.call_logging_service.set_tenant_context') as mock_context:
            
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_context.return_value = None
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            
            # Log the event
            await call_logging_service.log_call_event(
                call_id=call_id,
                tenant_id=tenant_id,
                event_type=event_type,
                message=message,
                level=level,
                metadata=metadata,
                agent_id=agent_id,
                duration_ms=duration_ms
            )
            
            # Property: Event must be stored in memory
            call_key = str(call_id)
            assert call_key in call_logging_service.active_call_logs
            
            logs = call_logging_service.active_call_logs[call_key]
            assert len(logs) == 1
            
            log_entry = logs[0]
            
            # Property: Log entry must have consistent data
            assert log_entry.call_id == call_id
            assert log_entry.tenant_id == tenant_id
            assert log_entry.event_type == event_type
            assert log_entry.message == message
            assert log_entry.level == level
            assert log_entry.metadata == metadata
            assert log_entry.agent_id == agent_id
            assert log_entry.duration_ms == duration_ms
            assert isinstance(log_entry.timestamp, datetime)
            
            # Property: Database persistence must be attempted
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @given(
        call_id=st.uuids(),
        tenant_id=st.uuids(),
        from_number=generate_phone_number(),
        to_number=generate_phone_number(),
        direction=st.sampled_from(list(CallDirection)),
        agent_id=st.one_of(st.none(), st.uuids())
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_call_logging_lifecycle_consistency(
        self, call_logging_service, call_id, tenant_id, from_number, 
        to_number, direction, agent_id
    ):
        """
        **Validates: Requirements 4.6, 8.4**
        
        Property 11: Call Activity Logging
        Call logging lifecycle must maintain consistency from start to end.
        """
        with patch('voicecore.services.call_logging_service.get_db_session') as mock_db, \
             patch('voicecore.services.call_logging_service.set_tenant_context') as mock_context:
            
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_context.return_value = None
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.execute = AsyncMock()
            
            # Mock call record for summary generation
            mock_call = MagicMock()
            mock_call.id = call_id
            mock_call.tenant_id = tenant_id
            mock_call.status = CallStatus.COMPLETED
            mock_call.direction = direction
            mock_call.from_number = from_number
            mock_call.to_number = to_number
            mock_call.duration = 120
            mock_call.talk_time = 100
            mock_call.wait_time = 20
            mock_call.ai_handled = False
            mock_call.ai_duration = 0
            mock_call.recording_url = None
            mock_call.recording_duration = None
            mock_call.transcript = None
            mock_call.transcript_confidence = None
            mock_call.detected_language = None
            mock_call.spam_score = 0.0
            mock_call.is_vip = False
            mock_call.customer_satisfaction = None
            mock_call.resolution_status = None
            mock_call.created_at = datetime.utcnow()
            mock_call.updated_at = datetime.utcnow()
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_call
            mock_session.execute.return_value = mock_result
            
            # Start call logging
            await call_logging_service.start_call_logging(
                call_id=call_id,
                tenant_id=tenant_id,
                from_number=from_number,
                to_number=to_number,
                direction=direction,
                agent_id=agent_id
            )
            
            # Property: Call initiation must be logged
            call_key = str(call_id)
            assert call_key in call_logging_service.active_call_logs
            
            logs = call_logging_service.active_call_logs[call_key]
            assert len(logs) >= 1
            
            initiation_log = logs[0]
            assert initiation_log.event_type == EventType.CALL_INITIATED
            assert from_number in initiation_log.metadata["from_number"]
            assert to_number in initiation_log.metadata["to_number"]
            assert direction.value in initiation_log.metadata["direction"]
            
            # Add some intermediate events
            await call_logging_service.log_call_event(
                call_id=call_id,
                tenant_id=tenant_id,
                event_type=EventType.CALL_ANSWERED,
                message="Call answered by agent",
                agent_id=agent_id
            )
            
            await call_logging_service.log_call_event(
                call_id=call_id,
                tenant_id=tenant_id,
                event_type=EventType.AI_INTERACTION_START,
                message="AI interaction started"
            )
            
            # End call logging
            summary = await call_logging_service.end_call_logging(
                call_id=call_id,
                tenant_id=tenant_id,
                end_reason="normal",
                final_status=CallStatus.COMPLETED
            )
            
            # Property: Call end must be logged
            logs = call_logging_service.active_call_logs.get(call_key, [])
            end_logs = [log for log in logs if log.event_type == EventType.CALL_ENDED]
            assert len(end_logs) >= 1
            
            end_log = end_logs[-1]
            assert "normal" in end_log.metadata["end_reason"]
            assert CallStatus.COMPLETED.value in end_log.metadata["final_status"]
            
            # Property: Summary must contain consistent data
            assert summary["call_id"] == str(call_id)
            assert summary["tenant_id"] == str(tenant_id)
            assert summary["status"] == CallStatus.COMPLETED.value
            assert summary["direction"] == direction.value
            assert summary["from_number"] == from_number
            assert summary["to_number"] == to_number
            
            # Property: In-memory logs must be cleaned up
            assert call_key not in call_logging_service.active_call_logs
    
    @given(
        call_id=st.uuids(),
        tenant_id=st.uuids(),
        recording_info=generate_recording_info()
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_call_recording_management_consistency(
        self, call_logging_service, call_id, tenant_id, recording_info
    ):
        """
        **Validates: Requirements 8.4**
        
        Property 11: Call Activity Logging
        Call recording management must maintain consistency and proper state tracking.
        """
        with patch('voicecore.services.call_logging_service.get_db_session') as mock_db, \
             patch('voicecore.services.call_logging_service.set_tenant_context') as mock_context, \
             patch.object(call_logging_service.twilio_service, 'start_recording') as mock_start, \
             patch.object(call_logging_service.twilio_service, 'get_recording_details') as mock_details:
            
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_context.return_value = None
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            
            # Mock call record lookup
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = "CA1234567890abcdef"
            mock_session.execute.return_value = mock_result
            
            # Mock Twilio service responses
            mock_start.return_value = {
                "recording_sid": recording_info.recording_sid,
                "status": "in-progress",
                "recording_url": recording_info.recording_url
            }
            
            mock_details.return_value = {
                "recording_sid": recording_info.recording_sid,
                "recording_url": recording_info.recording_url,
                "duration": recording_info.duration,
                "file_size": recording_info.file_size,
                "status": "completed"
            }
            
            # Start recording
            recording_sid = await call_logging_service.start_call_recording(
                call_id=call_id,
                tenant_id=tenant_id,
                twilio_call_sid="CA1234567890abcdef"
            )
            
            # Property: Recording must be tracked
            assert recording_sid == recording_info.recording_sid
            call_key = str(call_id)
            assert call_key in call_logging_service.recording_sessions
            
            session_info = call_logging_service.recording_sessions[call_key]
            assert session_info.recording_sid == recording_info.recording_sid
            assert session_info.status == "in-progress"
            
            # Property: Recording start must be logged
            assert call_key in call_logging_service.active_call_logs
            logs = call_logging_service.active_call_logs[call_key]
            recording_start_logs = [log for log in logs if log.event_type == EventType.CALL_RECORDING_STARTED]
            assert len(recording_start_logs) == 1
            
            start_log = recording_start_logs[0]
            assert start_log.metadata["recording_sid"] == recording_info.recording_sid
            
            # Stop recording
            final_recording_info = await call_logging_service.stop_call_recording(
                call_id=call_id,
                tenant_id=tenant_id
            )
            
            # Property: Recording session must be cleaned up
            assert call_key not in call_logging_service.recording_sessions
            
            # Property: Final recording info must be consistent
            assert final_recording_info.recording_sid == recording_info.recording_sid
            assert final_recording_info.status == "completed"
            assert final_recording_info.duration == recording_info.duration
            
            # Property: Recording stop must be logged
            logs = call_logging_service.active_call_logs[call_key]
            recording_stop_logs = [log for log in logs if log.event_type == EventType.CALL_RECORDING_STOPPED]
            assert len(recording_stop_logs) == 1
            
            stop_log = recording_stop_logs[0]
            assert stop_log.metadata["recording_sid"] == recording_info.recording_sid
            assert stop_log.metadata["duration"] == recording_info.duration
    
    @given(
        call_id=st.uuids(),
        tenant_id=st.uuids(),
        transcript_info=generate_transcript_info(),
        recording_url=st.text(min_size=20, max_size=100)
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_transcript_generation_consistency(
        self, call_logging_service, call_id, tenant_id, transcript_info, recording_url
    ):
        """
        **Validates: Requirements 6.6**
        
        Property 21: Automatic Transcription
        Transcript generation must be consistent and maintain quality metrics.
        """
        with patch('voicecore.services.call_logging_service.get_db_session') as mock_db, \
             patch('voicecore.services.call_logging_service.set_tenant_context') as mock_context, \
             patch('aiohttp.ClientSession.get') as mock_get, \
             patch('openai.AsyncOpenAI') as mock_openai, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', create=True) as mock_open:
            
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_context.return_value = None
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            
            # Mock HTTP response for recording download
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read.return_value = b"fake_audio_data"
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Mock OpenAI client and response
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            
            mock_transcript_response = MagicMock()
            mock_transcript_response.text = transcript_info.transcript_text
            mock_transcript_response.confidence = transcript_info.confidence_score
            mock_transcript_response.language = transcript_info.language
            mock_transcript_response.segments = transcript_info.segments
            
            mock_client.audio.transcriptions.create.return_value = mock_transcript_response
            
            # Mock temporary file
            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/test_audio.mp3"
            mock_temp.return_value.__enter__.return_value = mock_temp_file
            
            # Mock file operations
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Generate transcript
            result_transcript = await call_logging_service.generate_call_transcript(
                call_id=call_id,
                tenant_id=tenant_id,
                recording_url=recording_url,
                language=transcript_info.language
            )
            
            # Property: Transcript must have consistent data
            assert result_transcript.transcript_text == transcript_info.transcript_text
            assert result_transcript.confidence_score == transcript_info.confidence_score
            assert result_transcript.language == transcript_info.language
            assert result_transcript.word_count == len(transcript_info.transcript_text.split())
            assert isinstance(result_transcript.processing_time_ms, int)
            assert result_transcript.processing_time_ms > 0
            assert isinstance(result_transcript.created_at, datetime)
            
            # Property: Transcript generation must be logged
            call_key = str(call_id)
            if call_key in call_logging_service.active_call_logs:
                logs = call_logging_service.active_call_logs[call_key]
                transcript_logs = [log for log in logs if "transcript" in log.message.lower()]
                assert len(transcript_logs) >= 1
                
                transcript_log = transcript_logs[-1]
                assert transcript_log.metadata["transcript_length"] == len(transcript_info.transcript_text)
                assert transcript_log.metadata["word_count"] == result_transcript.word_count
                assert transcript_log.metadata["confidence_score"] == transcript_info.confidence_score
                assert transcript_log.metadata["language"] == transcript_info.language
            
            # Property: OpenAI API must be called correctly
            mock_client.audio.transcriptions.create.assert_called_once()
            call_args = mock_client.audio.transcriptions.create.call_args
            assert call_args.kwargs["model"] == call_logging_service.transcription_model
            assert call_args.kwargs["language"] == transcript_info.language
            assert call_args.kwargs["response_format"] == "verbose_json"
    
    @given(
        call_count=st.integers(min_value=1, max_value=10),
        events_per_call=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_concurrent_call_logging_isolation(
        self, call_logging_service, call_count, events_per_call
    ):
        """
        **Validates: Requirements 4.6, 8.4**
        
        Property 11: Call Activity Logging
        Concurrent call logging must maintain proper isolation between calls.
        """
        with patch('voicecore.services.call_logging_service.get_db_session') as mock_db, \
             patch('voicecore.services.call_logging_service.set_tenant_context') as mock_context:
            
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_context.return_value = None
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            
            # Create multiple calls with events
            call_data = []
            
            for i in range(call_count):
                call_id = uuid.uuid4()
                tenant_id = uuid.uuid4()
                call_data.append((call_id, tenant_id))
            
            # Log events concurrently for each call
            async def log_call_events(call_id, tenant_id):
                events_logged = 0
                
                for j in range(events_per_call):
                    event_type = EventType.CALL_INITIATED if j == 0 else EventType.AI_INTERACTION_START
                    
                    await call_logging_service.log_call_event(
                        call_id=call_id,
                        tenant_id=tenant_id,
                        event_type=event_type,
                        message=f"Event {j} for call {call_id}",
                        metadata={"event_index": j, "call_specific": str(call_id)}
                    )
                    events_logged += 1
                
                return events_logged
            
            # Execute concurrent logging
            tasks = [
                log_call_events(call_id, tenant_id)
                for call_id, tenant_id in call_data
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Property: All events must be logged successfully
            assert all(result == events_per_call for result in results)
            
            # Property: Each call must have isolated logs
            for call_id, tenant_id in call_data:
                call_key = str(call_id)
                assert call_key in call_logging_service.active_call_logs
                
                logs = call_logging_service.active_call_logs[call_key]
                assert len(logs) == events_per_call
                
                # Property: All logs must belong to the correct call
                for log in logs:
                    assert log.call_id == call_id
                    assert log.tenant_id == tenant_id
                    assert log.metadata["call_specific"] == str(call_id)
                
                # Property: Event indices must be preserved
                event_indices = [log.metadata["event_index"] for log in logs]
                assert sorted(event_indices) == list(range(events_per_call))
    
    @given(
        call_id=st.uuids(),
        tenant_id=st.uuids(),
        event_types=st.lists(generate_event_type(), min_size=1, max_size=10, unique=True),
        time_range_hours=st.integers(min_value=1, max_value=24)
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_call_log_filtering_consistency(
        self, call_logging_service, call_id, tenant_id, event_types, time_range_hours
    ):
        """
        **Validates: Requirements 4.6**
        
        Property 11: Call Activity Logging
        Call log filtering must consistently apply filters and maintain data integrity.
        """
        with patch('voicecore.services.call_logging_service.get_db_session') as mock_db, \
             patch('voicecore.services.call_logging_service.set_tenant_context') as mock_context:
            
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_context.return_value = None
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            
            # Log events of different types at different times
            base_time = datetime.utcnow()
            logged_events = []
            
            for i, event_type in enumerate(event_types):
                # Create events at different times
                event_time = base_time - timedelta(hours=i)
                
                # Manually create log entry with specific timestamp
                log_entry = CallLogEntry(
                    call_id=call_id,
                    tenant_id=tenant_id,
                    event_type=event_type,
                    timestamp=event_time,
                    level=LogLevel.INFO,
                    message=f"Test event {i}",
                    metadata={"event_index": i}
                )
                
                # Store in memory
                call_key = str(call_id)
                if call_key not in call_logging_service.active_call_logs:
                    call_logging_service.active_call_logs[call_key] = []
                call_logging_service.active_call_logs[call_key].append(log_entry)
                
                logged_events.append((event_type, event_time))
            
            # Test filtering by event types
            filter_event_types = event_types[:len(event_types)//2] if len(event_types) > 1 else event_types
            
            filtered_logs = await call_logging_service.get_call_logs(
                call_id=call_id,
                tenant_id=tenant_id,
                event_types=filter_event_types
            )
            
            # Property: Filtered logs must only contain requested event types
            returned_event_types = [log.event_type for log in filtered_logs]
            assert all(event_type in filter_event_types for event_type in returned_event_types)
            
            # Property: All requested event types must be present if they were logged
            expected_count = len([et for et in event_types if et in filter_event_types])
            assert len(filtered_logs) == expected_count
            
            # Test filtering by time range
            start_time = base_time - timedelta(hours=time_range_hours//2)
            end_time = base_time + timedelta(hours=1)
            
            time_filtered_logs = await call_logging_service.get_call_logs(
                call_id=call_id,
                tenant_id=tenant_id,
                start_time=start_time,
                end_time=end_time
            )
            
            # Property: Time filtered logs must be within the specified range
            for log in time_filtered_logs:
                assert start_time <= log.timestamp <= end_time
            
            # Property: Logs must be sorted by timestamp
            timestamps = [log.timestamp for log in time_filtered_logs]
            assert timestamps == sorted(timestamps)


if __name__ == "__main__":
    # Run property tests
    pytest.main([__file__, "-v", "--tb=short"])