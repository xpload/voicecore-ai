"""
Twilio integration service for VoiceCore AI.

Provides comprehensive Twilio Voice API integration with call management,
webhook handling, and enterprise-grade error handling and monitoring.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Dial, Number
from twilio.base.exceptions import TwilioException
from twilio.request_validator import RequestValidator

from voicecore.config import settings
from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import Call, CallEvent, Tenant, Agent, CallStatus, CallDirection, CallType
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils
from voicecore.services.call_routing_service import CallRoutingService, CallPriority
from sqlalchemy import update


logger = get_logger(__name__)


class TwilioServiceError(Exception):
    """Base exception for Twilio service errors."""
    pass


class CallNotFoundError(TwilioServiceError):
    """Raised when a call is not found."""
    pass


class InvalidWebhookError(TwilioServiceError):
    """Raised when webhook validation fails."""
    pass


class TwilioService:
    """
    Comprehensive Twilio Voice API integration service.
    
    Handles call initiation, management, webhook processing, and TwiML generation
    with enterprise-grade error handling and security compliance.
    """
    
    def __init__(self):
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self.validator = RequestValidator(settings.twilio_auth_token)
        self.routing_service = CallRoutingService()
        self.logger = logger
        
        # Circuit breaker for Twilio API calls
        self._failure_count = 0
        self._last_failure_time = 0
        self._circuit_open = False
        self._circuit_timeout = 60  # seconds
    
    async def initiate_call(
        self, 
        tenant_id: uuid.UUID,
        from_number: str, 
        to_number: str,
        call_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call through Twilio.
        
        Args:
            tenant_id: Tenant UUID
            from_number: Caller's phone number (Twilio number)
            to_number: Destination phone number
            call_data: Additional call metadata
            
        Returns:
            Dict containing call information and Twilio call SID
            
        Raises:
            TwilioServiceError: If call initiation fails
        """
        try:
            # Check circuit breaker
            if self._is_circuit_open():
                raise TwilioServiceError("Twilio service temporarily unavailable")
            
            # Validate phone numbers
            if not SecurityUtils.validate_phone_number(to_number):
                raise TwilioServiceError(f"Invalid destination phone number: {to_number}")
            
            # Create webhook URL for call status updates
            webhook_url = f"{settings.twilio_webhook_url}/webhooks/twilio/status"
            
            # Initiate call through Twilio
            twilio_call = self.client.calls.create(
                to=to_number,
                from_=from_number,
                url=f"{settings.twilio_webhook_url}/webhooks/twilio/voice",
                status_callback=webhook_url,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                timeout=30,
                record=True if call_data and call_data.get('record', False) else False
            )
            
            # Create call record in database
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                call = Call(
                    tenant_id=tenant_id,
                    twilio_call_sid=twilio_call.sid,
                    from_number=from_number,
                    to_number=to_number,
                    direction=CallDirection.OUTBOUND,
                    status=CallStatus.INITIATED,
                    call_type=CallType.CUSTOMER,
                    metadata=call_data or {}
                )
                
                session.add(call)
                await session.commit()
                
                # Log call initiation
                await self._log_call_event(
                    session, call.id, "call_initiated", 
                    {"twilio_sid": twilio_call.sid, "direction": "outbound"}
                )
            
            self._reset_circuit_breaker()
            
            self.logger.call_started(
                call_sid=twilio_call.sid,
                tenant_id=str(tenant_id),
                from_number=from_number,
                to_number=to_number,
                direction="outbound"
            )
            
            return {
                "call_sid": twilio_call.sid,
                "status": twilio_call.status,
                "direction": "outbound",
                "from": from_number,
                "to": to_number,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except TwilioException as e:
            self._handle_twilio_error(e)
            raise TwilioServiceError(f"Failed to initiate call: {str(e)}")
        except Exception as e:
            self.logger.error("Call initiation failed", error=str(e))
            raise TwilioServiceError(f"Call initiation failed: {str(e)}")
    
    async def handle_incoming_call(
        self, 
        call_sid: str, 
        from_number: str, 
        to_number: str,
        tenant_id: Optional[uuid.UUID] = None
    ) -> str:
        """
        Handle incoming call and generate TwiML response.
        
        Args:
            call_sid: Twilio call SID
            from_number: Caller's phone number
            to_number: Called number (tenant's Twilio number)
            tenant_id: Optional tenant ID (will be resolved from phone number)
            
        Returns:
            TwiML response string
        """
        try:
            # Resolve tenant from phone number if not provided
            if not tenant_id:
                tenant_id = await self._resolve_tenant_from_number(to_number)
                
            if not tenant_id:
                return self._generate_error_twiml("Service temporarily unavailable")
            
            # Create call record
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Check if call already exists
                existing_call = await self._get_call_by_sid(session, call_sid)
                
                if not existing_call:
                    call = Call(
                        tenant_id=tenant_id,
                        twilio_call_sid=call_sid,
                        from_number=from_number,
                        to_number=to_number,
                        direction=CallDirection.INBOUND,
                        status=CallStatus.RINGING,
                        call_type=CallType.CUSTOMER,
                        started_at=datetime.utcnow()
                    )
                    
                    session.add(call)
                    await session.flush()
                    
                    # Log call event
                    await self._log_call_event(
                        session, call.id, "call_received", 
                        {"from": from_number, "to": to_number}
                    )
                    
                    await session.commit()
                else:
                    call = existing_call
            
            # Check for spam with comprehensive analysis
            spam_analysis = await self._analyze_spam_comprehensive(tenant_id, from_number, call_sid)
            spam_score = spam_analysis.score
            
            if spam_analysis.should_block:
                # Log spam detection
                await self._log_spam_detection(
                    tenant_id=tenant_id,
                    call_sid=call_sid,
                    phone_number=from_number,
                    spam_analysis=spam_analysis
                )
                
                self.logger.info(
                    "Spam call blocked",
                    phone_number=from_number,
                    spam_score=spam_score,
                    reasons=spam_analysis.reasons,
                    call_sid=call_sid
                )
                
                return self._generate_spam_action_twiml(spam_analysis)
            
            elif spam_analysis.should_challenge:
                # Challenge suspicious calls
                self.logger.info(
                    "Spam call challenged",
                    phone_number=from_number,
                    spam_score=spam_score,
                    reasons=spam_analysis.reasons,
                    call_sid=call_sid
                )
                
                return self._generate_spam_challenge_twiml(spam_analysis)
            
            # Check for VIP caller
            is_vip = await self._check_vip_caller(tenant_id, from_number)
            
            # Generate TwiML for AI handling
            twiml_response = await self._generate_ai_handling_twiml(
                tenant_id, call_sid, from_number, is_vip
            )
            
            self.logger.call_started(
                call_sid=call_sid,
                tenant_id=str(tenant_id),
                from_number=from_number,
                to_number=to_number,
                direction="inbound",
                is_vip=is_vip,
                spam_score=spam_score
            )
            
            return twiml_response
            
        except Exception as e:
            self.logger.error("Incoming call handling failed", call_sid=call_sid, error=str(e))
            return self._generate_error_twiml("Unable to process call")
    
    async def transfer_call(
        self, 
        call_sid: str, 
        target_agent_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> bool:
        """
        Transfer an active call to an agent.
        
        Args:
            call_sid: Twilio call SID
            target_agent_id: Agent UUID to transfer to
            tenant_id: Tenant UUID
            
        Returns:
            bool: True if transfer was successful
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get call and agent information
                call = await self._get_call_by_sid(session, call_sid)
                if not call:
                    raise CallNotFoundError(f"Call {call_sid} not found")
                
                agent = await session.get(Agent, target_agent_id)
                if not agent or not agent.is_available:
                    raise TwilioServiceError("Target agent not available")
                
                # Update call status
                call.status = CallStatus.TRANSFERRED
                call.agent_id = target_agent_id
                
                # Create transfer event
                await self._log_call_event(
                    session, call.id, "call_transferred",
                    {"target_agent": str(target_agent_id), "agent_name": agent.name}
                )
                
                await session.commit()
            
            # Execute transfer through Twilio
            twilio_call = self.client.calls(call_sid).fetch()
            
            # Generate transfer TwiML
            transfer_twiml = self._generate_transfer_twiml(agent.phone_number or agent.extension)
            
            # Update the call with new TwiML
            twilio_call.update(twiml=transfer_twiml)
            
            self.logger.call_transfer(
                call_sid=call_sid,
                from_ai=True,
                to_agent=agent.name,
                agent_id=str(target_agent_id)
            )
            
            return True
            
        except TwilioException as e:
            self.logger.error("Call transfer failed", call_sid=call_sid, error=str(e))
            return False
        except Exception as e:
            self.logger.error("Call transfer failed", call_sid=call_sid, error=str(e))
            return False
    
    async def end_call(self, call_sid: str, tenant_id: uuid.UUID) -> bool:
        """
        End an active call.
        
        Args:
            call_sid: Twilio call SID
            tenant_id: Tenant UUID
            
        Returns:
            bool: True if call was ended successfully
        """
        try:
            # End call through Twilio
            twilio_call = self.client.calls(call_sid)
            twilio_call.update(status='completed')
            
            # Update call record
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                call = await self._get_call_by_sid(session, call_sid)
                if call:
                    call.status = CallStatus.COMPLETED
                    call.ended_at = datetime.utcnow()
                    
                    if call.started_at:
                        call.duration = int((call.ended_at - call.started_at).total_seconds())
                    
                    await self._log_call_event(
                        session, call.id, "call_ended",
                        {"duration": call.duration, "status": "completed"}
                    )
                    
                    await session.commit()
            
            self.logger.call_ended(
                call_sid=call_sid,
                duration=call.duration if call else 0,
                status="completed"
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Call termination failed", call_sid=call_sid, error=str(e))
            return False
    
    async def get_call_status(self, call_sid: str) -> Optional[Dict[str, Any]]:
        """
        Get current call status from Twilio.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            Optional[Dict]: Call status information or None if not found
        """
        try:
            twilio_call = self.client.calls(call_sid).fetch()
            
            return {
                "sid": twilio_call.sid,
                "status": twilio_call.status,
                "direction": twilio_call.direction,
                "from": twilio_call.from_,
                "to": twilio_call.to,
                "duration": twilio_call.duration,
                "start_time": twilio_call.start_time.isoformat() if twilio_call.start_time else None,
                "end_time": twilio_call.end_time.isoformat() if twilio_call.end_time else None,
                "price": twilio_call.price,
                "price_unit": twilio_call.price_unit
            }
            
        except TwilioException as e:
            self.logger.error("Failed to get call status", call_sid=call_sid, error=str(e))
            return None
    
    def validate_webhook(self, url: str, params: Dict[str, Any], signature: str) -> bool:
        """
        Validate Twilio webhook signature for security.
        
        Args:
            url: Webhook URL
            params: Request parameters
            signature: X-Twilio-Signature header
            
        Returns:
            bool: True if signature is valid
        """
        try:
            return self.validator.validate(url, params, signature)
        except Exception as e:
            self.logger.error("Webhook validation failed", error=str(e))
            return False
    
    async def process_status_webhook(
        self, 
        call_sid: str, 
        call_status: str, 
        webhook_data: Dict[str, Any]
    ) -> bool:
        """
        Process Twilio status webhook updates.
        
        Args:
            call_sid: Twilio call SID
            call_status: New call status
            webhook_data: Webhook payload data
            
        Returns:
            bool: True if processed successfully
        """
        try:
            async with get_db_session() as session:
                # Find call by Twilio SID
                call = await self._get_call_by_sid(session, call_sid)
                
                if not call:
                    self.logger.warning("Received webhook for unknown call", call_sid=call_sid)
                    return False
                
                await set_tenant_context(session, str(call.tenant_id))
                
                # Update call status
                old_status = call.status
                call.status = self._map_twilio_status(call_status)
                
                # Update timing information
                if call_status == 'answered' and not call.started_at:
                    call.started_at = datetime.utcnow()
                elif call_status in ['completed', 'failed', 'no-answer', 'busy']:
                    if not call.ended_at:
                        call.ended_at = datetime.utcnow()
                    
                    if call.started_at and call.ended_at:
                        call.duration = int((call.ended_at - call.started_at).total_seconds())
                
                # Update cost information if available
                if 'CallPrice' in webhook_data and webhook_data['CallPrice']:
                    try:
                        call.cost_cents = int(float(webhook_data['CallPrice']) * 100)
                    except (ValueError, TypeError):
                        pass
                
                # Log status change event
                await self._log_call_event(
                    session, call.id, "status_changed",
                    {
                        "old_status": old_status.value if old_status else None,
                        "new_status": call.status.value,
                        "twilio_status": call_status,
                        "webhook_data": SecurityUtils.sanitize_data(webhook_data)
                    }
                )
                
                await session.commit()
                
                self.logger.info(
                    "Call status updated",
                    call_sid=call_sid,
                    old_status=old_status.value if old_status else None,
                    new_status=call.status.value,
                    duration=call.duration
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Status webhook processing failed", call_sid=call_sid, error=str(e))
            return False
    
    # Private helper methods
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self._circuit_open:
            return False
        
        if datetime.utcnow().timestamp() - self._last_failure_time > self._circuit_timeout:
            self._circuit_open = False
            self._failure_count = 0
            return False
        
        return True
    
    def _handle_twilio_error(self, error: TwilioException):
        """Handle Twilio API errors and update circuit breaker."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow().timestamp()
        
        if self._failure_count >= 5:  # Open circuit after 5 failures
            self._circuit_open = True
        
        self.logger.external_service_error(
            service="twilio",
            operation="api_call",
            error_code=str(error.code) if hasattr(error, 'code') else "unknown",
            error_message=str(error)
        )
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker after successful operation."""
        self._failure_count = 0
        self._circuit_open = False
    
    async def _resolve_tenant_from_number(self, phone_number: str) -> Optional[uuid.UUID]:
        """Resolve tenant ID from Twilio phone number."""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    "SELECT id FROM tenants WHERE twilio_phone_number = :phone_number",
                    {"phone_number": phone_number}
                )
                tenant_row = result.fetchone()
                return tenant_row[0] if tenant_row else None
        except Exception as e:
            self.logger.error("Failed to resolve tenant from number", phone_number=phone_number, error=str(e))
            return None
    
    async def _get_call_by_sid(self, session, call_sid: str) -> Optional[Call]:
        """Get call by Twilio SID."""
        result = await session.execute(
            "SELECT * FROM calls WHERE twilio_call_sid = :call_sid",
            {"call_sid": call_sid}
        )
        call_row = result.fetchone()
        if call_row:
            return Call(**dict(call_row._mapping))
        return None
    
    async def _log_call_event(
        self, 
        session, 
        call_id: uuid.UUID, 
        event_type: str, 
        event_data: Dict[str, Any]
    ):
        """Log call event to database."""
        event = CallEvent(
            call_id=call_id,
            event_type=event_type,
            event_data=SecurityUtils.sanitize_data(event_data),
            timestamp=datetime.utcnow()
        )
        session.add(event)
    
    async def _check_spam(self, tenant_id: uuid.UUID, phone_number: str, call_context: Optional[Dict[str, Any]] = None) -> float:
        """Check if phone number is spam using comprehensive spam detection."""
        try:
            from voicecore.services.spam_detection_service import SpamDetectionService
            
            spam_service = SpamDetectionService()
            spam_score = await spam_service.analyze_call(tenant_id, phone_number, call_context)
            
            return spam_score.score
            
        except Exception as e:
            self.logger.error("Spam detection failed", error=str(e))
            # Return safe default on error
            return 0.0
    
    async def _check_vip_caller(self, tenant_id: uuid.UUID, phone_number: str) -> bool:
        """Check if caller is VIP."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    "SELECT vip_phone_numbers FROM tenant_settings WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                settings_row = result.fetchone()
                
                if settings_row and settings_row[0]:
                    vip_numbers = settings_row[0]
                    return phone_number in vip_numbers
                
                return False
        except Exception:
            return False
    
    def _map_twilio_status(self, twilio_status: str) -> CallStatus:
        """Map Twilio status to internal call status."""
        status_mapping = {
            'queued': CallStatus.INITIATED,
            'initiated': CallStatus.INITIATED,
            'ringing': CallStatus.RINGING,
            'answered': CallStatus.IN_PROGRESS,
            'in-progress': CallStatus.IN_PROGRESS,
            'completed': CallStatus.COMPLETED,
            'failed': CallStatus.FAILED,
            'busy': CallStatus.BUSY,
            'no-answer': CallStatus.NO_ANSWER,
            'canceled': CallStatus.CANCELLED
        }
        return status_mapping.get(twilio_status, CallStatus.FAILED)
    
    def _generate_error_twiml(self, message: str) -> str:
        """Generate error TwiML response."""
        response = VoiceResponse()
        response.say(message, voice='alice', language='en')
        response.hangup()
        return str(response)
    
    def _generate_spam_rejection_twiml(self) -> str:
        """Generate TwiML for spam call rejection."""
        response = VoiceResponse()
        response.say("This number has been identified as spam. Goodbye.", voice='alice', language='en')
        response.hangup()
        return str(response)
    
    async def _generate_ai_handling_twiml(
        self, 
        tenant_id: uuid.UUID, 
        call_sid: str, 
        from_number: str,
        is_vip: bool = False
    ) -> str:
        """Generate TwiML for AI handling of the call."""
        response = VoiceResponse()
        
        # Get tenant settings for personalized greeting
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    "SELECT welcome_message, ai_name, ai_voice_id FROM tenant_settings WHERE tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                settings_row = result.fetchone()
                
                if settings_row:
                    welcome_message = settings_row[0] or "Hello! How may I assist you today?"
                    ai_name = settings_row[1] or "Sofia"
                    voice = settings_row[2] or "alice"
                else:
                    welcome_message = "Hello! How may I assist you today?"
                    ai_name = "Sofia"
                    voice = "alice"
        except Exception:
            welcome_message = "Hello! How may I assist you today?"
            ai_name = "Sofia"
            voice = "alice"
        
        # Add VIP greeting if applicable
        if is_vip:
            welcome_message = f"Hello! Thank you for being a valued customer. I'm {ai_name}. {welcome_message}"
        else:
            welcome_message = f"Hello! I'm {ai_name}, your AI assistant. {welcome_message}"
        
        # Generate AI conversation TwiML
        response.say(welcome_message, voice=voice, language='en')
        
        # Gather input for AI processing with enhanced parameters
        gather = Gather(
            input='speech',
            timeout=10,
            speech_timeout='auto',
            action=f"{settings.twilio_webhook_url}/webhooks/twilio/ai-response",
            method='POST',
            enhanced=True,  # Enable enhanced speech recognition
            speech_model='experimental_conversations',  # Use conversation model
            profanity_filter=False  # Let AI handle content filtering
        )
        gather.say("Please tell me how I can help you today.", voice=voice, language='en')
        response.append(gather)
        
        # Fallback if no input - try once more before transferring
        response.say("I didn't hear anything. Let me try again.", voice=voice, language='en')
        
        # Second attempt gather
        gather2 = Gather(
            input='speech',
            timeout=8,
            speech_timeout='auto',
            action=f"{settings.twilio_webhook_url}/webhooks/twilio/ai-response",
            method='POST'
        )
        gather2.say("How may I assist you?", voice=voice, language='en')
        response.append(gather2)
        
        # Final fallback - transfer to customer service
        response.say("I'm having trouble hearing you. Let me transfer you to our customer service team.", voice=voice, language='en')
        response.redirect(f"{settings.twilio_webhook_url}/webhooks/twilio/transfer")
        
        return str(response)
    
    def _generate_transfer_twiml(self, target_number: str) -> str:
        """Generate TwiML for call transfer."""
        response = VoiceResponse()
        response.say("Please hold while I transfer your call.", voice='alice', language='en')
        
        dial = Dial(timeout=30, record=True)
        dial.number(target_number)
        response.append(dial)
        
        # Fallback if transfer fails
        response.say("I'm sorry, the transfer failed. Please try calling back later.", voice='alice', language='en')
        response.hangup()
        
        return str(response)
    
    async def _analyze_spam_comprehensive(
        self, 
        tenant_id: uuid.UUID, 
        phone_number: str, 
        call_sid: str
    ):
        """Perform comprehensive spam analysis using the spam detection service."""
        try:
            from voicecore.services.spam_detection_service import SpamDetectionService
            
            spam_service = SpamDetectionService()
            
            # Prepare call context
            call_context = {
                "call_sid": call_sid,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "twilio_webhook"
            }
            
            # Analyze the call
            spam_analysis = await spam_service.analyze_call(
                tenant_id=tenant_id,
                phone_number=phone_number,
                call_context=call_context
            )
            
            return spam_analysis
            
        except Exception as e:
            self.logger.error("Comprehensive spam analysis failed", error=str(e))
            # Return safe default
            from voicecore.services.spam_detection_service import SpamScore
            return SpamScore(
                score=0.0,
                reasons=["Analysis error"],
                action="allow",
                triggered_rules=[],
                confidence=0.0
            )
    
    async def _log_spam_detection(
        self,
        tenant_id: uuid.UUID,
        call_sid: str,
        phone_number: str,
        spam_analysis
    ):
        """Log spam detection event for analytics and reporting."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from voicecore.models import SpamReport
                
                # Create spam report
                spam_report = SpamReport(
                    tenant_id=tenant_id,
                    phone_number=phone_number,
                    spam_score=spam_analysis.score,
                    triggered_rules=[str(rule_id) for rule_id in spam_analysis.triggered_rules],
                    detection_method="automatic",
                    action_taken=spam_analysis.action,
                    call_content=f"Call SID: {call_sid}",
                    metadata={
                        "call_sid": call_sid,
                        "reasons": spam_analysis.reasons,
                        "confidence": spam_analysis.confidence,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                session.add(spam_report)
                await session.commit()
                
                # Update call record with spam information
                await session.execute(
                    update(Call)
                    .where(Call.twilio_call_sid == call_sid)
                    .values(
                        call_type=CallType.SPAM,
                        spam_score=spam_analysis.score,
                        spam_reasons=spam_analysis.reasons
                    )
                )
                await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to log spam detection", error=str(e))
    
    def _generate_spam_action_twiml(self, spam_analysis) -> str:
        """Generate TwiML based on spam analysis action."""
        response = VoiceResponse()
        
        if spam_analysis.action == "block":
            # Use custom message if available from triggered rules
            message = "This call has been blocked due to spam detection. Goodbye."
            
            # Check if any triggered rule has a custom response message
            # This would require fetching the rule details, simplified for now
            response.say(message, voice='alice', language='en')
            response.hangup()
            
        elif spam_analysis.action == "challenge":
            return self._generate_spam_challenge_twiml(spam_analysis)
            
        else:  # flag or allow
            # Log but allow the call to proceed
            response.say("Please hold while we connect your call.", voice='alice', language='en')
            response.redirect(f"{settings.twilio_webhook_url}/webhooks/twilio/route")
        
        return str(response)
    
    def _generate_spam_challenge_twiml(self, spam_analysis) -> str:
        """Generate TwiML for spam challenge (human verification)."""
        response = VoiceResponse()
        
        # Simple challenge - press a random number
        import random
        challenge_number = random.randint(1, 9)
        
        response.say(
            f"To verify you are not a robocall, please press {challenge_number} on your keypad.",
            voice='alice',
            language='en'
        )
        
        # Gather the response
        gather = Gather(
            input='dtmf',
            timeout=10,
            num_digits=1,
            action=f"{settings.twilio_webhook_url}/webhooks/twilio/spam-challenge",
            method='POST'
        )
        gather.say(f"Press {challenge_number} now.", voice='alice', language='en')
        response.append(gather)
        
        # Store challenge answer in call metadata for verification
        # This would need to be implemented in the webhook handler
        
        # Fallback if no response
        response.say("No response received. This call will be terminated.", voice='alice', language='en')
        response.hangup()
        
        return str(response)
    
    def _generate_spam_rejection_twiml(self) -> str:
        """Generate TwiML for spam call rejection (legacy method)."""
        response = VoiceResponse()
        response.say("This number has been identified as spam. Goodbye.", voice='alice', language='en')
        response.hangup()
        return str(response)
    
    # Recording Management Methods
    
    async def start_recording(
        self,
        call_sid: str,
        record_channels: str = "dual",
        recording_format: str = "mp3"
    ) -> Dict[str, Any]:
        """
        Start recording for an active call.
        
        Args:
            call_sid: Twilio call SID
            record_channels: Recording channels (mono/dual)
            recording_format: Recording format (mp3/wav)
            
        Returns:
            Dict containing recording information
            
        Raises:
            TwilioServiceError: If recording start fails
        """
        try:
            # Check circuit breaker
            if self._is_circuit_open():
                raise TwilioServiceError("Twilio service temporarily unavailable")
            
            # Start recording via Twilio API
            recording = self.client.calls(call_sid).recordings.create(
                recording_channels=record_channels,
                recording_status_callback=f"{settings.twilio_webhook_url}/webhooks/twilio/recording-status",
                recording_status_callback_method="POST"
            )
            
            self.logger.info(
                "Call recording started",
                call_sid=call_sid,
                recording_sid=recording.sid,
                channels=record_channels,
                format=recording_format
            )
            
            return {
                "recording_sid": recording.sid,
                "status": recording.status,
                "recording_url": recording.uri,
                "channels": record_channels,
                "format": recording_format
            }
            
        except TwilioException as e:
            self._handle_circuit_breaker_failure()
            self.logger.error("Failed to start call recording", error=str(e), call_sid=call_sid)
            raise TwilioServiceError(f"Failed to start recording: {str(e)}")
        except Exception as e:
            self.logger.error("Unexpected error starting recording", error=str(e), call_sid=call_sid)
            raise TwilioServiceError(f"Unexpected error starting recording: {str(e)}")
    
    async def stop_recording(self, call_sid: str, recording_sid: str) -> Dict[str, Any]:
        """
        Stop an active recording.
        
        Args:
            call_sid: Twilio call SID
            recording_sid: Twilio recording SID
            
        Returns:
            Dict containing final recording information
            
        Raises:
            TwilioServiceError: If recording stop fails
        """
        try:
            # Check circuit breaker
            if self._is_circuit_open():
                raise TwilioServiceError("Twilio service temporarily unavailable")
            
            # Stop recording via Twilio API
            recording = self.client.calls(call_sid).recordings(recording_sid).update(
                status='stopped'
            )
            
            self.logger.info(
                "Call recording stopped",
                call_sid=call_sid,
                recording_sid=recording_sid,
                final_status=recording.status
            )
            
            return {
                "recording_sid": recording.sid,
                "status": recording.status,
                "recording_url": recording.uri,
                "duration": recording.duration,
                "file_size": getattr(recording, 'file_size', 0)
            }
            
        except TwilioException as e:
            self._handle_circuit_breaker_failure()
            self.logger.error("Failed to stop call recording", error=str(e), call_sid=call_sid)
            raise TwilioServiceError(f"Failed to stop recording: {str(e)}")
        except Exception as e:
            self.logger.error("Unexpected error stopping recording", error=str(e), call_sid=call_sid)
            raise TwilioServiceError(f"Unexpected error stopping recording: {str(e)}")
    
    async def get_recording_details(self, recording_sid: str) -> Dict[str, Any]:
        """
        Get details for a specific recording.
        
        Args:
            recording_sid: Twilio recording SID
            
        Returns:
            Dict containing recording details
            
        Raises:
            TwilioServiceError: If recording retrieval fails
        """
        try:
            # Check circuit breaker
            if self._is_circuit_open():
                raise TwilioServiceError("Twilio service temporarily unavailable")
            
            # Get recording details from Twilio
            recording = self.client.recordings(recording_sid).fetch()
            
            # Build recording URL (Twilio provides relative URI)
            recording_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
            
            return {
                "recording_sid": recording.sid,
                "call_sid": recording.call_sid,
                "status": recording.status,
                "recording_url": recording_url,
                "duration": recording.duration,
                "file_size": getattr(recording, 'file_size', 0),
                "channels": getattr(recording, 'channels', 1),
                "created_at": recording.date_created.isoformat() if recording.date_created else None,
                "updated_at": recording.date_updated.isoformat() if recording.date_updated else None
            }
            
        except TwilioException as e:
            self._handle_circuit_breaker_failure()
            self.logger.error("Failed to get recording details", error=str(e), recording_sid=recording_sid)
            raise TwilioServiceError(f"Failed to get recording details: {str(e)}")
        except Exception as e:
            self.logger.error("Unexpected error getting recording details", error=str(e), recording_sid=recording_sid)
            raise TwilioServiceError(f"Unexpected error getting recording details: {str(e)}")
    
    async def list_call_recordings(self, call_sid: str) -> List[Dict[str, Any]]:
        """
        List all recordings for a specific call.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            List of recording dictionaries
            
        Raises:
            TwilioServiceError: If recording list retrieval fails
        """
        try:
            # Check circuit breaker
            if self._is_circuit_open():
                raise TwilioServiceError("Twilio service temporarily unavailable")
            
            # Get recordings for the call
            recordings = self.client.recordings.list(call_sid=call_sid)
            
            recording_list = []
            for recording in recordings:
                recording_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
                
                recording_list.append({
                    "recording_sid": recording.sid,
                    "call_sid": recording.call_sid,
                    "status": recording.status,
                    "recording_url": recording_url,
                    "duration": recording.duration,
                    "file_size": getattr(recording, 'file_size', 0),
                    "channels": getattr(recording, 'channels', 1),
                    "created_at": recording.date_created.isoformat() if recording.date_created else None,
                    "updated_at": recording.date_updated.isoformat() if recording.date_updated else None
                })
            
            return recording_list
            
        except TwilioException as e:
            self._handle_circuit_breaker_failure()
            self.logger.error("Failed to list call recordings", error=str(e), call_sid=call_sid)
            raise TwilioServiceError(f"Failed to list recordings: {str(e)}")
        except Exception as e:
            self.logger.error("Unexpected error listing recordings", error=str(e), call_sid=call_sid)
            raise TwilioServiceError(f"Unexpected error listing recordings: {str(e)}")
    
    async def delete_recording(self, recording_sid: str) -> bool:
        """
        Delete a recording from Twilio.
        
        Args:
            recording_sid: Twilio recording SID
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            TwilioServiceError: If recording deletion fails
        """
        try:
            # Check circuit breaker
            if self._is_circuit_open():
                raise TwilioServiceError("Twilio service temporarily unavailable")
            
            # Delete recording from Twilio
            self.client.recordings(recording_sid).delete()
            
            self.logger.info("Recording deleted successfully", recording_sid=recording_sid)
            return True
            
        except TwilioException as e:
            self._handle_circuit_breaker_failure()
            self.logger.error("Failed to delete recording", error=str(e), recording_sid=recording_sid)
            raise TwilioServiceError(f"Failed to delete recording: {str(e)}")
        except Exception as e:
            self.logger.error("Unexpected error deleting recording", error=str(e), recording_sid=recording_sid)
            raise TwilioServiceError(f"Unexpected error deleting recording: {str(e)}")