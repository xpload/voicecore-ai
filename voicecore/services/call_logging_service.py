"""
Call Logging service for VoiceCore AI.

Provides comprehensive call activity logging, recording integration,
and transcript generation for analytics and compliance purposes.
"""

import uuid
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import Call, CallEvent, CallStatus, CallDirection, CallType, Agent
from voicecore.logging import get_logger
from voicecore.config import settings
from voicecore.services.twilio_service import TwilioService


logger = get_logger(__name__)


class LogLevel(Enum):
    """Log level enumeration for call events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(Enum):
    """Call event types for comprehensive tracking."""
    CALL_INITIATED = "call_initiated"
    CALL_RINGING = "call_ringing"
    CALL_ANSWERED = "call_answered"
    CALL_TRANSFERRED = "call_transferred"
    CALL_HOLD = "call_hold"
    CALL_UNHOLD = "call_unhold"
    CALL_MUTED = "call_muted"
    CALL_UNMUTED = "call_unmuted"
    CALL_RECORDING_STARTED = "call_recording_started"
    CALL_RECORDING_STOPPED = "call_recording_stopped"
    CALL_ENDED = "call_ended"
    AGENT_ASSIGNED = "agent_assigned"
    AGENT_UNASSIGNED = "agent_unassigned"
    AI_INTERACTION_START = "ai_interaction_start"
    AI_INTERACTION_END = "ai_interaction_end"
    AI_TRANSFER_ATTEMPT = "ai_transfer_attempt"
    SPAM_DETECTED = "spam_detected"
    VIP_IDENTIFIED = "vip_identified"
    EMOTION_DETECTED = "emotion_detected"
    QUALITY_ISSUE = "quality_issue"
    ESCALATION_TRIGGERED = "escalation_triggered"
    CALLBACK_REQUESTED = "callback_requested"
    VOICEMAIL_LEFT = "voicemail_left"


@dataclass
class CallLogEntry:
    """Represents a call log entry with comprehensive metadata."""
    call_id: uuid.UUID
    tenant_id: uuid.UUID
    event_type: EventType
    timestamp: datetime
    level: LogLevel
    message: str
    metadata: Dict[str, Any]
    agent_id: Optional[uuid.UUID] = None
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["call_id"] = str(self.call_id)
        data["tenant_id"] = str(self.tenant_id)
        data["event_type"] = self.event_type.value
        data["level"] = self.level.value
        data["timestamp"] = self.timestamp.isoformat()
        if self.agent_id:
            data["agent_id"] = str(self.agent_id)
        return data


@dataclass
class RecordingInfo:
    """Information about call recording."""
    recording_sid: str
    recording_url: str
    duration: int
    file_size: int
    format: str
    status: str
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


@dataclass
class TranscriptInfo:
    """Information about call transcript."""
    transcript_text: str
    confidence_score: float
    language: str
    word_count: int
    processing_time_ms: int
    created_at: datetime
    segments: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


class CallLoggingServiceError(Exception):
    """Base exception for call logging service errors."""
    pass


class RecordingError(CallLoggingServiceError):
    """Raised when call recording operations fail."""
    pass


class TranscriptionError(CallLoggingServiceError):
    """Raised when transcript generation fails."""
    pass


class CallLoggingService:
    """
    Call Logging service for comprehensive call activity tracking.
    
    Handles call event logging, recording management, transcript generation,
    and analytics data collection for the VoiceCore AI system.
    """
    
    def __init__(self):
        self.logger = logger
        self.twilio_service = TwilioService()
        
        # Storage configuration
        self.recording_storage_bucket = getattr(settings, 'recording_storage_bucket', 'voicecore-recordings')
        self.transcript_storage_bucket = getattr(settings, 'transcript_storage_bucket', 'voicecore-transcripts')
        
        # Recording settings
        self.auto_recording_enabled = getattr(settings, 'auto_recording_enabled', True)
        self.recording_format = getattr(settings, 'recording_format', 'mp3')
        self.recording_channels = getattr(settings, 'recording_channels', 'dual')
        
        # Transcription settings
        self.auto_transcription_enabled = getattr(settings, 'auto_transcription_enabled', True)
        self.transcription_language = getattr(settings, 'transcription_language', 'auto')
        self.transcription_model = getattr(settings, 'transcription_model', 'whisper-1')
        
        # In-memory storage for real-time logging
        self.active_call_logs: Dict[str, List[CallLogEntry]] = {}
        self.recording_sessions: Dict[str, RecordingInfo] = {}
    
    async def log_call_event(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID,
        event_type: EventType,
        message: str,
        level: LogLevel = LogLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[uuid.UUID] = None,
        duration_ms: Optional[int] = None
    ) -> None:
        """
        Log a call event with comprehensive metadata.
        
        Args:
            call_id: Call UUID
            tenant_id: Tenant UUID
            event_type: Type of event
            message: Human-readable event message
            level: Log level
            metadata: Additional event metadata
            agent_id: Agent involved in the event
            duration_ms: Event duration in milliseconds
        """
        try:
            # Create log entry
            log_entry = CallLogEntry(
                call_id=call_id,
                tenant_id=tenant_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                level=level,
                message=message,
                metadata=metadata or {},
                agent_id=agent_id,
                duration_ms=duration_ms
            )
            
            # Store in memory for real-time access
            call_key = str(call_id)
            if call_key not in self.active_call_logs:
                self.active_call_logs[call_key] = []
            self.active_call_logs[call_key].append(log_entry)
            
            # Persist to database
            await self._persist_call_event(log_entry)
            
            # Log to system logger
            self.logger.log(
                level.value.upper(),
                f"Call Event: {event_type.value}",
                call_id=str(call_id),
                tenant_id=str(tenant_id),
                agent_id=str(agent_id) if agent_id else None,
                message=message,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error("Failed to log call event", error=str(e), call_id=str(call_id))
            raise CallLoggingServiceError(f"Failed to log call event: {str(e)}")
    
    async def start_call_logging(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID,
        from_number: str,
        to_number: str,
        direction: CallDirection,
        agent_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Start comprehensive logging for a new call.
        
        Args:
            call_id: Call UUID
            tenant_id: Tenant UUID
            from_number: Caller's number
            to_number: Called number
            direction: Call direction
            agent_id: Agent handling the call
        """
        try:
            # Log call initiation
            await self.log_call_event(
                call_id=call_id,
                tenant_id=tenant_id,
                event_type=EventType.CALL_INITIATED,
                message=f"Call initiated from {from_number} to {to_number}",
                level=LogLevel.INFO,
                metadata={
                    "from_number": from_number,
                    "to_number": to_number,
                    "direction": direction.value,
                    "initiated_at": datetime.utcnow().isoformat()
                },
                agent_id=agent_id
            )
            
            # Start recording if enabled
            if self.auto_recording_enabled:
                await self.start_call_recording(call_id, tenant_id)
            
            self.logger.info(
                "Call logging started",
                call_id=str(call_id),
                tenant_id=str(tenant_id),
                direction=direction.value
            )
            
        except Exception as e:
            self.logger.error("Failed to start call logging", error=str(e), call_id=str(call_id))
            raise CallLoggingServiceError(f"Failed to start call logging: {str(e)}")
    
    async def end_call_logging(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID,
        end_reason: str = "normal",
        final_status: CallStatus = CallStatus.COMPLETED
    ) -> Dict[str, Any]:
        """
        End call logging and generate final summary.
        
        Args:
            call_id: Call UUID
            tenant_id: Tenant UUID
            end_reason: Reason for call ending
            final_status: Final call status
            
        Returns:
            Dict[str, Any]: Call summary with metrics
        """
        try:
            # Log call end
            await self.log_call_event(
                call_id=call_id,
                tenant_id=tenant_id,
                event_type=EventType.CALL_ENDED,
                message=f"Call ended: {end_reason}",
                level=LogLevel.INFO,
                metadata={
                    "end_reason": end_reason,
                    "final_status": final_status.value,
                    "ended_at": datetime.utcnow().isoformat()
                }
            )
            
            # Stop recording if active
            if str(call_id) in self.recording_sessions:
                await self.stop_call_recording(call_id, tenant_id)
            
            # Generate call summary
            summary = await self._generate_call_summary(call_id, tenant_id)
            
            # Start transcript generation if enabled
            if self.auto_transcription_enabled and summary.get("recording_url"):
                asyncio.create_task(
                    self.generate_call_transcript(call_id, tenant_id, summary["recording_url"])
                )
            
            # Clean up in-memory logs
            call_key = str(call_id)
            if call_key in self.active_call_logs:
                del self.active_call_logs[call_key]
            
            self.logger.info(
                "Call logging ended",
                call_id=str(call_id),
                tenant_id=str(tenant_id),
                summary=summary
            )
            
            return summary
            
        except Exception as e:
            self.logger.error("Failed to end call logging", error=str(e), call_id=str(call_id))
            raise CallLoggingServiceError(f"Failed to end call logging: {str(e)}")
    
    async def start_call_recording(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID,
        twilio_call_sid: Optional[str] = None
    ) -> str:
        """
        Start call recording.
        
        Args:
            call_id: Call UUID
            tenant_id: Tenant UUID
            twilio_call_sid: Twilio call SID
            
        Returns:
            str: Recording SID
        """
        try:
            # Get Twilio call SID if not provided
            if not twilio_call_sid:
                async with get_db_session() as session:
                    await set_tenant_context(session, str(tenant_id))
                    
                    from sqlalchemy import select
                    result = await session.execute(
                        select(Call.twilio_call_sid).where(Call.id == call_id)
                    )
                    twilio_call_sid = result.scalar_one_or_none()
                    
                    if not twilio_call_sid:
                        raise RecordingError("Twilio call SID not found")
            
            # Start recording via Twilio
            recording_result = await self.twilio_service.start_recording(
                call_sid=twilio_call_sid,
                record_channels=self.recording_channels,
                recording_format=self.recording_format
            )
            
            # Store recording info
            recording_info = RecordingInfo(
                recording_sid=recording_result["recording_sid"],
                recording_url=recording_result.get("recording_url", ""),
                duration=0,
                file_size=0,
                format=self.recording_format,
                status="in-progress",
                created_at=datetime.utcnow()
            )
            
            self.recording_sessions[str(call_id)] = recording_info
            
            # Log recording start
            await self.log_call_event(
                call_id=call_id,
                tenant_id=tenant_id,
                event_type=EventType.CALL_RECORDING_STARTED,
                message="Call recording started",
                level=LogLevel.INFO,
                metadata={
                    "recording_sid": recording_info.recording_sid,
                    "format": self.recording_format,
                    "channels": self.recording_channels
                }
            )
            
            self.logger.info(
                "Call recording started",
                call_id=str(call_id),
                recording_sid=recording_info.recording_sid
            )
            
            return recording_info.recording_sid
            
        except Exception as e:
            self.logger.error("Failed to start call recording", error=str(e), call_id=str(call_id))
            raise RecordingError(f"Failed to start recording: {str(e)}")
    
    async def stop_call_recording(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Optional[RecordingInfo]:
        """
        Stop call recording and retrieve final recording info.
        
        Args:
            call_id: Call UUID
            tenant_id: Tenant UUID
            
        Returns:
            Optional[RecordingInfo]: Recording information if available
        """
        try:
            call_key = str(call_id)
            
            if call_key not in self.recording_sessions:
                self.logger.warning("No active recording session found", call_id=str(call_id))
                return None
            
            recording_info = self.recording_sessions[call_key]
            
            # Get final recording details from Twilio
            recording_details = await self.twilio_service.get_recording_details(
                recording_info.recording_sid
            )
            
            # Update recording info
            recording_info.recording_url = recording_details.get("recording_url", "")
            recording_info.duration = recording_details.get("duration", 0)
            recording_info.file_size = recording_details.get("file_size", 0)
            recording_info.status = recording_details.get("status", "completed")
            
            # Update call record with recording info
            await self._update_call_recording_info(call_id, tenant_id, recording_info)
            
            # Log recording stop
            await self.log_call_event(
                call_id=call_id,
                tenant_id=tenant_id,
                event_type=EventType.CALL_RECORDING_STOPPED,
                message="Call recording stopped",
                level=LogLevel.INFO,
                metadata={
                    "recording_sid": recording_info.recording_sid,
                    "duration": recording_info.duration,
                    "file_size": recording_info.file_size,
                    "recording_url": recording_info.recording_url
                }
            )
            
            # Clean up session
            del self.recording_sessions[call_key]
            
            self.logger.info(
                "Call recording stopped",
                call_id=str(call_id),
                recording_sid=recording_info.recording_sid,
                duration=recording_info.duration
            )
            
            return recording_info
            
        except Exception as e:
            self.logger.error("Failed to stop call recording", error=str(e), call_id=str(call_id))
            raise RecordingError(f"Failed to stop recording: {str(e)}")
    
    async def generate_call_transcript(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID,
        recording_url: str,
        language: Optional[str] = None
    ) -> TranscriptInfo:
        """
        Generate transcript from call recording.
        
        Args:
            call_id: Call UUID
            tenant_id: Tenant UUID
            recording_url: URL to the call recording
            language: Language for transcription (auto-detect if None)
            
        Returns:
            TranscriptInfo: Transcript information
        """
        try:
            start_time = datetime.utcnow()
            
            # Use OpenAI Whisper for transcription
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=getattr(settings, 'openai_api_key'))
            
            # Download recording file (in production, this would be optimized)
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(recording_url) as response:
                    if response.status != 200:
                        raise TranscriptionError(f"Failed to download recording: {response.status}")
                    
                    audio_data = await response.read()
            
            # Create temporary file for transcription
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Transcribe using OpenAI Whisper
                with open(temp_file_path, 'rb') as audio_file:
                    transcript_response = await client.audio.transcriptions.create(
                        model=self.transcription_model,
                        file=audio_file,
                        language=language or self.transcription_language,
                        response_format="verbose_json",
                        timestamp_granularities=["segment"]
                    )
                
                # Process transcript response
                processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                transcript_info = TranscriptInfo(
                    transcript_text=transcript_response.text,
                    confidence_score=getattr(transcript_response, 'confidence', 0.95),
                    language=getattr(transcript_response, 'language', language or 'en'),
                    word_count=len(transcript_response.text.split()),
                    processing_time_ms=processing_time,
                    created_at=datetime.utcnow(),
                    segments=getattr(transcript_response, 'segments', [])
                )
                
                # Update call record with transcript
                await self._update_call_transcript_info(call_id, tenant_id, transcript_info)
                
                # Log transcript generation
                await self.log_call_event(
                    call_id=call_id,
                    tenant_id=tenant_id,
                    event_type=EventType.AI_INTERACTION_END,  # Using existing event type
                    message="Call transcript generated",
                    level=LogLevel.INFO,
                    metadata={
                        "transcript_length": len(transcript_info.transcript_text),
                        "word_count": transcript_info.word_count,
                        "confidence_score": transcript_info.confidence_score,
                        "language": transcript_info.language,
                        "processing_time_ms": processing_time
                    }
                )
                
                self.logger.info(
                    "Call transcript generated",
                    call_id=str(call_id),
                    word_count=transcript_info.word_count,
                    confidence=transcript_info.confidence_score,
                    processing_time_ms=processing_time
                )
                
                return transcript_info
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
            
        except Exception as e:
            self.logger.error("Failed to generate call transcript", error=str(e), call_id=str(call_id))
            raise TranscriptionError(f"Failed to generate transcript: {str(e)}")
    
    async def get_call_logs(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID,
        event_types: Optional[List[EventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[CallLogEntry]:
        """
        Get call logs for a specific call.
        
        Args:
            call_id: Call UUID
            tenant_id: Tenant UUID
            event_types: Filter by specific event types
            start_time: Filter events after this time
            end_time: Filter events before this time
            
        Returns:
            List[CallLogEntry]: List of call log entries
        """
        try:
            # Check in-memory logs first
            call_key = str(call_id)
            if call_key in self.active_call_logs:
                logs = self.active_call_logs[call_key]
            else:
                # Retrieve from database
                logs = await self._retrieve_call_events_from_db(
                    call_id, tenant_id, event_types, start_time, end_time
                )
            
            # Apply filters
            filtered_logs = logs
            
            if event_types:
                event_type_values = [et.value for et in event_types]
                filtered_logs = [log for log in filtered_logs if log.event_type.value in event_type_values]
            
            if start_time:
                filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]
            
            if end_time:
                filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]
            
            # Sort by timestamp
            filtered_logs.sort(key=lambda x: x.timestamp)
            
            return filtered_logs
            
        except Exception as e:
            self.logger.error("Failed to get call logs", error=str(e), call_id=str(call_id))
            raise CallLoggingServiceError(f"Failed to get call logs: {str(e)}")
    
    async def get_call_summary(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get comprehensive call summary with all logged data.
        
        Args:
            call_id: Call UUID
            tenant_id: Tenant UUID
            
        Returns:
            Dict[str, Any]: Call summary
        """
        try:
            return await self._generate_call_summary(call_id, tenant_id)
            
        except Exception as e:
            self.logger.error("Failed to get call summary", error=str(e), call_id=str(call_id))
            raise CallLoggingServiceError(f"Failed to get call summary: {str(e)}")
    
    # Private helper methods
    
    async def _persist_call_event(self, log_entry: CallLogEntry) -> None:
        """Persist call event to database."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(log_entry.tenant_id))
                
                call_event = CallEvent(
                    call_id=log_entry.call_id,
                    tenant_id=log_entry.tenant_id,
                    event_type=log_entry.event_type.value,
                    event_data=log_entry.metadata,
                    timestamp=log_entry.timestamp,
                    agent_id=log_entry.agent_id
                )
                
                session.add(call_event)
                await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to persist call event", error=str(e))
            # Don't raise exception to avoid breaking call flow
    
    async def _update_call_recording_info(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID,
        recording_info: RecordingInfo
    ) -> None:
        """Update call record with recording information."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import update
                await session.execute(
                    update(Call)
                    .where(Call.id == call_id)
                    .values(
                        recording_url=recording_info.recording_url,
                        recording_duration=recording_info.duration
                    )
                )
                await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to update call recording info", error=str(e))
    
    async def _update_call_transcript_info(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID,
        transcript_info: TranscriptInfo
    ) -> None:
        """Update call record with transcript information."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import update
                await session.execute(
                    update(Call)
                    .where(Call.id == call_id)
                    .values(
                        transcript=transcript_info.transcript_text,
                        transcript_confidence=transcript_info.confidence_score,
                        detected_language=transcript_info.language
                    )
                )
                await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to update call transcript info", error=str(e))
    
    async def _generate_call_summary(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Generate comprehensive call summary."""
        try:
            # Get call record
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select
                result = await session.execute(
                    select(Call).where(Call.id == call_id)
                )
                call = result.scalar_one_or_none()
                
                if not call:
                    raise CallLoggingServiceError("Call not found")
            
            # Get call events
            logs = await self.get_call_logs(call_id, tenant_id)
            
            # Calculate metrics
            total_events = len(logs)
            event_types = list(set(log.event_type.value for log in logs))
            
            # Get recording info
            recording_info = None
            if str(call_id) in self.recording_sessions:
                recording_info = self.recording_sessions[str(call_id)].to_dict()
            elif call.recording_url:
                recording_info = {
                    "recording_url": call.recording_url,
                    "duration": call.recording_duration,
                    "status": "completed"
                }
            
            # Build summary
            summary = {
                "call_id": str(call_id),
                "tenant_id": str(tenant_id),
                "status": call.status.value,
                "direction": call.direction.value,
                "from_number": call.from_number,
                "to_number": call.to_number,
                "duration": call.duration,
                "talk_time": call.talk_time,
                "wait_time": call.wait_time,
                "ai_handled": call.ai_handled,
                "ai_duration": call.ai_duration,
                "recording_info": recording_info,
                "transcript_available": bool(call.transcript),
                "transcript_confidence": call.transcript_confidence,
                "detected_language": call.detected_language,
                "spam_score": call.spam_score,
                "is_vip": call.is_vip,
                "customer_satisfaction": call.customer_satisfaction,
                "resolution_status": call.resolution_status,
                "total_events": total_events,
                "event_types": event_types,
                "created_at": call.created_at.isoformat(),
                "updated_at": call.updated_at.isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error("Failed to generate call summary", error=str(e))
            raise
    
    async def _retrieve_call_events_from_db(
        self,
        call_id: uuid.UUID,
        tenant_id: uuid.UUID,
        event_types: Optional[List[EventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[CallLogEntry]:
        """Retrieve call events from database."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, and_
                
                query = select(CallEvent).where(CallEvent.call_id == call_id)
                
                if event_types:
                    event_type_values = [et.value for et in event_types]
                    query = query.where(CallEvent.event_type.in_(event_type_values))
                
                if start_time:
                    query = query.where(CallEvent.timestamp >= start_time)
                
                if end_time:
                    query = query.where(CallEvent.timestamp <= end_time)
                
                query = query.order_by(CallEvent.timestamp)
                
                result = await session.execute(query)
                events = result.scalars().all()
                
                # Convert to CallLogEntry objects
                log_entries = []
                for event in events:
                    log_entry = CallLogEntry(
                        call_id=event.call_id,
                        tenant_id=event.tenant_id,
                        event_type=EventType(event.event_type),
                        timestamp=event.timestamp,
                        level=LogLevel.INFO,  # Default level for DB events
                        message=f"Event: {event.event_type}",
                        metadata=event.event_data or {},
                        agent_id=event.agent_id
                    )
                    log_entries.append(log_entry)
                
                return log_entries
                
        except Exception as e:
            self.logger.error("Failed to retrieve call events from database", error=str(e))
            return []