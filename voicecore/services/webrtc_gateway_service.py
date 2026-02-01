"""
WebRTC Gateway service for VoiceCore AI.

Provides WebRTC signaling server, browser-based calling interface,
and call quality monitoring for the multitenant virtual receptionist system.
"""

import uuid
import json
import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import Agent, Call, CallStatus, CallDirection
from voicecore.logging import get_logger
from voicecore.config import settings
from voicecore.services.twilio_service import TwilioService


logger = get_logger(__name__)


class WebRTCConnectionState(Enum):
    """WebRTC connection states."""
    NEW = "new"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    CLOSED = "closed"


class CallQuality(Enum):
    """Call quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"


@dataclass
class WebRTCPeer:
    """Represents a WebRTC peer connection."""
    peer_id: str
    agent_id: uuid.UUID
    tenant_id: uuid.UUID
    connection_state: WebRTCConnectionState
    ice_connection_state: str
    signaling_state: str
    created_at: datetime
    last_activity: datetime
    call_id: Optional[uuid.UUID] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["connection_state"] = self.connection_state.value
        data["created_at"] = self.created_at.isoformat()
        data["last_activity"] = self.last_activity.isoformat()
        if self.call_id:
            data["call_id"] = str(self.call_id)
        if self.agent_id:
            data["agent_id"] = str(self.agent_id)
        if self.tenant_id:
            data["tenant_id"] = str(self.tenant_id)
        return data


@dataclass
class CallQualityMetrics:
    """Call quality metrics for monitoring."""
    peer_id: str
    timestamp: datetime
    audio_level: float
    packet_loss: float
    jitter: float
    round_trip_time: float
    bandwidth_kbps: float
    quality_score: float
    quality_level: CallQuality
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["quality_level"] = self.quality_level.value
        return data


class WebRTCGatewayError(Exception):
    """Base exception for WebRTC gateway errors."""
    pass


class PeerNotFoundError(WebRTCGatewayError):
    """Raised when a peer is not found."""
    pass


class InvalidSignalingMessageError(WebRTCGatewayError):
    """Raised when a signaling message is invalid."""
    pass


class WebRTCGatewayService:
    """
    WebRTC Gateway service for browser-based calling.
    
    Handles WebRTC signaling, peer connection management, call quality monitoring,
    and integration with Twilio for PSTN connectivity.
    """
    
    def __init__(self):
        self.logger = logger
        self.peers: Dict[str, WebRTCPeer] = {}
        self.call_sessions: Dict[str, Dict[str, Any]] = {}
        self.quality_metrics: Dict[str, List[CallQualityMetrics]] = {}
        self.twilio_service = TwilioService()
        
        # WebSocket connections for signaling
        self.websocket_connections: Dict[str, Any] = {}
        
        # STUN/TURN server configuration
        self.ice_servers = [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"},
        ]
        
        # Add TURN servers if configured
        if hasattr(settings, 'turn_server_url') and settings.turn_server_url:
            self.ice_servers.append({
                "urls": settings.turn_server_url,
                "username": getattr(settings, 'turn_username', ''),
                "credential": getattr(settings, 'turn_password', '')
            })
    
    async def create_peer_connection(
        self,
        agent_id: uuid.UUID,
        tenant_id: uuid.UUID,
        websocket_connection: Any
    ) -> str:
        """
        Create a new WebRTC peer connection for an agent.
        
        Args:
            agent_id: Agent UUID
            tenant_id: Tenant UUID
            websocket_connection: WebSocket connection for signaling
            
        Returns:
            str: Peer ID
        """
        try:
            peer_id = f"peer_{uuid.uuid4().hex[:16]}"
            
            # Verify agent exists and is active
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                from sqlalchemy import select, and_
                result = await session.execute(
                    select(Agent).where(
                        and_(
                            Agent.id == agent_id,
                            Agent.tenant_id == tenant_id,
                            Agent.is_active == True
                        )
                    )
                )
                agent = result.scalar_one_or_none()
                
                if not agent:
                    raise WebRTCGatewayError(f"Agent {agent_id} not found or inactive")
            
            # Create peer connection
            peer = WebRTCPeer(
                peer_id=peer_id,
                agent_id=agent_id,
                tenant_id=tenant_id,
                connection_state=WebRTCConnectionState.NEW,
                ice_connection_state="new",
                signaling_state="stable",
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            
            self.peers[peer_id] = peer
            self.websocket_connections[peer_id] = websocket_connection
            self.quality_metrics[peer_id] = []
            
            self.logger.info(
                "WebRTC peer connection created",
                peer_id=peer_id,
                agent_id=str(agent_id),
                tenant_id=str(tenant_id)
            )
            
            return peer_id
            
        except Exception as e:
            self.logger.error("Failed to create peer connection", error=str(e))
            raise WebRTCGatewayError(f"Failed to create peer connection: {str(e)}")
    
    async def handle_signaling_message(
        self,
        peer_id: str,
        message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle WebRTC signaling messages.
        
        Args:
            peer_id: Peer ID
            message: Signaling message
            
        Returns:
            Optional[Dict[str, Any]]: Response message if needed
        """
        try:
            if peer_id not in self.peers:
                raise PeerNotFoundError(f"Peer {peer_id} not found")
            
            peer = self.peers[peer_id]
            peer.last_activity = datetime.utcnow()
            
            message_type = message.get("type")
            
            if message_type == "offer":
                return await self._handle_offer(peer, message)
            elif message_type == "answer":
                return await self._handle_answer(peer, message)
            elif message_type == "ice-candidate":
                return await self._handle_ice_candidate(peer, message)
            elif message_type == "connection-state":
                return await self._handle_connection_state(peer, message)
            elif message_type == "quality-metrics":
                return await self._handle_quality_metrics(peer, message)
            elif message_type == "call-request":
                return await self._handle_call_request(peer, message)
            elif message_type == "call-answer":
                return await self._handle_call_answer(peer, message)
            elif message_type == "call-hangup":
                return await self._handle_call_hangup(peer, message)
            else:
                raise InvalidSignalingMessageError(f"Unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(
                "Failed to handle signaling message",
                peer_id=peer_id,
                message_type=message.get("type"),
                error=str(e)
            )
            return {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def initiate_outbound_call(
        self,
        peer_id: str,
        target_number: str,
        call_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call through WebRTC to PSTN.
        
        Args:
            peer_id: Peer ID of the calling agent
            target_number: Target phone number
            call_context: Additional call context
            
        Returns:
            Dict[str, Any]: Call initiation result
        """
        try:
            if peer_id not in self.peers:
                raise PeerNotFoundError(f"Peer {peer_id} not found")
            
            peer = self.peers[peer_id]
            
            # Create call record
            call_id = uuid.uuid4()
            
            async with get_db_session() as session:
                await set_tenant_context(session, str(peer.tenant_id))
                
                call = Call(
                    id=call_id,
                    tenant_id=peer.tenant_id,
                    agent_id=peer.agent_id,
                    from_number=f"agent_{peer.agent_id}",
                    to_number=target_number,
                    direction=CallDirection.OUTBOUND,
                    status=CallStatus.INITIATED,
                    twilio_call_sid="",  # Will be set when Twilio call is created
                    metadata={
                        "webrtc_peer_id": peer_id,
                        "call_context": call_context or {},
                        "initiated_via": "webrtc_softphone"
                    }
                )
                
                session.add(call)
                await session.commit()
            
            # Update peer with call information
            peer.call_id = call_id
            
            # Initiate Twilio call for PSTN connectivity
            # This would create a conference or use Twilio's WebRTC integration
            twilio_call_result = await self._create_twilio_webrtc_call(
                peer, target_number, call_id
            )
            
            # Store call session
            self.call_sessions[str(call_id)] = {
                "peer_id": peer_id,
                "target_number": target_number,
                "status": "initiated",
                "created_at": datetime.utcnow(),
                "twilio_call_sid": twilio_call_result.get("call_sid"),
                "context": call_context or {}
            }
            
            self.logger.info(
                "Outbound call initiated",
                peer_id=peer_id,
                call_id=str(call_id),
                target_number=target_number,
                twilio_call_sid=twilio_call_result.get("call_sid")
            )
            
            return {
                "type": "call-initiated",
                "call_id": str(call_id),
                "target_number": target_number,
                "status": "initiated",
                "twilio_call_sid": twilio_call_result.get("call_sid"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to initiate outbound call",
                peer_id=peer_id,
                target_number=target_number,
                error=str(e)
            )
            raise WebRTCGatewayError(f"Failed to initiate call: {str(e)}")
    
    async def handle_incoming_call(
        self,
        agent_id: uuid.UUID,
        call_id: uuid.UUID,
        caller_number: str,
        twilio_call_sid: str
    ) -> bool:
        """
        Handle incoming call routing to WebRTC agent.
        
        Args:
            agent_id: Target agent ID
            call_id: Call ID
            caller_number: Caller's phone number
            twilio_call_sid: Twilio call SID
            
        Returns:
            bool: True if call was successfully routed
        """
        try:
            # Find active peer for the agent
            agent_peer = None
            for peer in self.peers.values():
                if (peer.agent_id == agent_id and 
                    peer.connection_state == WebRTCConnectionState.CONNECTED):
                    agent_peer = peer
                    break
            
            if not agent_peer:
                self.logger.warning(
                    "No active WebRTC peer found for agent",
                    agent_id=str(agent_id)
                )
                return False
            
            # Update peer with call information
            agent_peer.call_id = call_id
            
            # Store call session
            self.call_sessions[str(call_id)] = {
                "peer_id": agent_peer.peer_id,
                "caller_number": caller_number,
                "status": "ringing",
                "created_at": datetime.utcnow(),
                "twilio_call_sid": twilio_call_sid,
                "direction": "inbound"
            }
            
            # Send incoming call notification to agent
            await self._send_to_peer(agent_peer.peer_id, {
                "type": "incoming-call",
                "call_id": str(call_id),
                "caller_number": caller_number,
                "twilio_call_sid": twilio_call_sid,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            self.logger.info(
                "Incoming call routed to WebRTC agent",
                agent_id=str(agent_id),
                call_id=str(call_id),
                caller_number=caller_number,
                peer_id=agent_peer.peer_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to handle incoming call",
                agent_id=str(agent_id),
                call_id=str(call_id),
                error=str(e)
            )
            return False
    
    async def get_call_quality_metrics(
        self,
        peer_id: str,
        time_range_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get call quality metrics for a peer.
        
        Args:
            peer_id: Peer ID
            time_range_minutes: Time range in minutes
            
        Returns:
            List[Dict[str, Any]]: Quality metrics
        """
        try:
            if peer_id not in self.quality_metrics:
                return []
            
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_range_minutes)
            
            recent_metrics = [
                metric.to_dict()
                for metric in self.quality_metrics[peer_id]
                if metric.timestamp >= cutoff_time
            ]
            
            return recent_metrics
            
        except Exception as e:
            self.logger.error("Failed to get quality metrics", peer_id=peer_id, error=str(e))
            return []
    
    async def get_peer_status(self, peer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get peer connection status.
        
        Args:
            peer_id: Peer ID
            
        Returns:
            Optional[Dict[str, Any]]: Peer status or None if not found
        """
        try:
            if peer_id not in self.peers:
                return None
            
            peer = self.peers[peer_id]
            
            # Get recent quality metrics
            recent_metrics = await self.get_call_quality_metrics(peer_id, 1)
            current_quality = CallQuality.UNKNOWN
            
            if recent_metrics:
                latest_metric = recent_metrics[-1]
                current_quality = CallQuality(latest_metric["quality_level"])
            
            return {
                "peer_id": peer_id,
                "agent_id": str(peer.agent_id),
                "tenant_id": str(peer.tenant_id),
                "connection_state": peer.connection_state.value,
                "ice_connection_state": peer.ice_connection_state,
                "signaling_state": peer.signaling_state,
                "call_id": str(peer.call_id) if peer.call_id else None,
                "current_quality": current_quality.value,
                "created_at": peer.created_at.isoformat(),
                "last_activity": peer.last_activity.isoformat(),
                "metrics_count": len(self.quality_metrics.get(peer_id, []))
            }
            
        except Exception as e:
            self.logger.error("Failed to get peer status", peer_id=peer_id, error=str(e))
            return None
    
    async def disconnect_peer(self, peer_id: str, reason: str = "normal") -> bool:
        """
        Disconnect a WebRTC peer.
        
        Args:
            peer_id: Peer ID
            reason: Disconnection reason
            
        Returns:
            bool: True if disconnected successfully
        """
        try:
            if peer_id not in self.peers:
                return False
            
            peer = self.peers[peer_id]
            
            # End any active call
            if peer.call_id:
                await self._end_peer_call(peer, reason)
            
            # Update peer state
            peer.connection_state = WebRTCConnectionState.CLOSED
            peer.last_activity = datetime.utcnow()
            
            # Send disconnect message
            await self._send_to_peer(peer_id, {
                "type": "disconnect",
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Clean up resources
            self.peers.pop(peer_id, None)
            self.websocket_connections.pop(peer_id, None)
            self.quality_metrics.pop(peer_id, None)
            
            self.logger.info(
                "WebRTC peer disconnected",
                peer_id=peer_id,
                reason=reason,
                agent_id=str(peer.agent_id)
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to disconnect peer", peer_id=peer_id, error=str(e))
            return False
    
    async def get_active_peers(self, tenant_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
        """
        Get list of active WebRTC peers.
        
        Args:
            tenant_id: Optional tenant filter
            
        Returns:
            List[Dict[str, Any]]: List of active peers
        """
        try:
            active_peers = []
            
            for peer in self.peers.values():
                if tenant_id and peer.tenant_id != tenant_id:
                    continue
                
                if peer.connection_state in [WebRTCConnectionState.CONNECTED, WebRTCConnectionState.CONNECTING]:
                    peer_status = await self.get_peer_status(peer.peer_id)
                    if peer_status:
                        active_peers.append(peer_status)
            
            return active_peers
            
        except Exception as e:
            self.logger.error("Failed to get active peers", error=str(e))
            return []
    
    # Private helper methods
    
    async def _handle_offer(self, peer: WebRTCPeer, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WebRTC offer."""
        peer.signaling_state = "have-remote-offer"
        
        # In a real implementation, this would process the SDP offer
        # and generate an appropriate answer
        
        return {
            "type": "ice-servers",
            "ice_servers": self.ice_servers,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_answer(self, peer: WebRTCPeer, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle WebRTC answer."""
        peer.signaling_state = "stable"
        return None
    
    async def _handle_ice_candidate(self, peer: WebRTCPeer, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle ICE candidate."""
        # In a real implementation, this would process ICE candidates
        return None
    
    async def _handle_connection_state(self, peer: WebRTCPeer, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle connection state updates."""
        connection_state = message.get("connection_state")
        ice_state = message.get("ice_connection_state")
        
        if connection_state:
            try:
                peer.connection_state = WebRTCConnectionState(connection_state)
            except ValueError:
                self.logger.warning(f"Invalid connection state: {connection_state}")
        
        if ice_state:
            peer.ice_connection_state = ice_state
        
        self.logger.debug(
            "Peer connection state updated",
            peer_id=peer.peer_id,
            connection_state=connection_state,
            ice_state=ice_state
        )
        
        return None
    
    async def _handle_quality_metrics(self, peer: WebRTCPeer, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle call quality metrics."""
        try:
            metrics_data = message.get("metrics", {})
            
            # Calculate quality score and level
            packet_loss = metrics_data.get("packet_loss", 0.0)
            jitter = metrics_data.get("jitter", 0.0)
            rtt = metrics_data.get("round_trip_time", 0.0)
            
            quality_score = self._calculate_quality_score(packet_loss, jitter, rtt)
            quality_level = self._determine_quality_level(quality_score)
            
            metrics = CallQualityMetrics(
                peer_id=peer.peer_id,
                timestamp=datetime.utcnow(),
                audio_level=metrics_data.get("audio_level", 0.0),
                packet_loss=packet_loss,
                jitter=jitter,
                round_trip_time=rtt,
                bandwidth_kbps=metrics_data.get("bandwidth_kbps", 0.0),
                quality_score=quality_score,
                quality_level=quality_level
            )
            
            # Store metrics (keep last 100 entries per peer)
            if peer.peer_id not in self.quality_metrics:
                self.quality_metrics[peer.peer_id] = []
            
            self.quality_metrics[peer.peer_id].append(metrics)
            
            # Keep only recent metrics
            if len(self.quality_metrics[peer.peer_id]) > 100:
                self.quality_metrics[peer.peer_id] = self.quality_metrics[peer.peer_id][-100:]
            
            # Update peer quality metrics
            peer.quality_metrics = metrics.to_dict()
            
            # Send quality feedback if needed
            if quality_level in [CallQuality.POOR, CallQuality.FAIR]:
                return {
                    "type": "quality-warning",
                    "quality_level": quality_level.value,
                    "quality_score": quality_score,
                    "recommendations": self._get_quality_recommendations(metrics),
                    "timestamp": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            self.logger.error("Failed to handle quality metrics", error=str(e))
        
        return None
    
    async def _handle_call_request(self, peer: WebRTCPeer, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound call request."""
        target_number = message.get("target_number")
        call_context = message.get("context", {})
        
        if not target_number:
            return {
                "type": "error",
                "error": "Target number is required",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            result = await self.initiate_outbound_call(peer.peer_id, target_number, call_context)
            return result
        except Exception as e:
            return {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_call_answer(self, peer: WebRTCPeer, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle call answer."""
        call_id = message.get("call_id")
        
        if not call_id or call_id not in self.call_sessions:
            return {
                "type": "error",
                "error": "Invalid call ID",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Update call session status
        self.call_sessions[call_id]["status"] = "answered"
        self.call_sessions[call_id]["answered_at"] = datetime.utcnow()
        
        # Update database call status
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(peer.tenant_id))
                
                from sqlalchemy import update
                await session.execute(
                    update(Call)
                    .where(Call.id == uuid.UUID(call_id))
                    .values(status=CallStatus.IN_PROGRESS)
                )
                await session.commit()
        except Exception as e:
            self.logger.error("Failed to update call status", call_id=call_id, error=str(e))
        
        return {
            "type": "call-answered",
            "call_id": call_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_call_hangup(self, peer: WebRTCPeer, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle call hangup."""
        call_id = message.get("call_id")
        reason = message.get("reason", "normal")
        
        if call_id and call_id in self.call_sessions:
            await self._end_call_session(call_id, reason)
        
        if peer.call_id:
            await self._end_peer_call(peer, reason)
        
        return {
            "type": "call-ended",
            "call_id": call_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _create_twilio_webrtc_call(
        self,
        peer: WebRTCPeer,
        target_number: str,
        call_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Create Twilio call for WebRTC integration."""
        try:
            # This would use Twilio's WebRTC integration or conference functionality
            # For now, return a mock response
            
            mock_call_sid = f"CA{uuid.uuid4().hex[:32]}"
            
            # Update call record with Twilio SID
            async with get_db_session() as session:
                await set_tenant_context(session, str(peer.tenant_id))
                
                from sqlalchemy import update
                await session.execute(
                    update(Call)
                    .where(Call.id == call_id)
                    .values(twilio_call_sid=mock_call_sid)
                )
                await session.commit()
            
            return {
                "call_sid": mock_call_sid,
                "status": "initiated"
            }
            
        except Exception as e:
            self.logger.error("Failed to create Twilio WebRTC call", error=str(e))
            raise
    
    async def _send_to_peer(self, peer_id: str, message: Dict[str, Any]):
        """Send message to peer via WebSocket."""
        try:
            if peer_id in self.websocket_connections:
                websocket = self.websocket_connections[peer_id]
                await websocket.send_text(json.dumps(message))
        except Exception as e:
            self.logger.error("Failed to send message to peer", peer_id=peer_id, error=str(e))
    
    async def _end_peer_call(self, peer: WebRTCPeer, reason: str):
        """End call for a peer."""
        if peer.call_id:
            call_id = str(peer.call_id)
            
            # End call session
            await self._end_call_session(call_id, reason)
            
            # Clear peer call reference
            peer.call_id = None
    
    async def _end_call_session(self, call_id: str, reason: str):
        """End a call session."""
        try:
            if call_id in self.call_sessions:
                session = self.call_sessions[call_id]
                session["status"] = "ended"
                session["ended_at"] = datetime.utcnow()
                session["end_reason"] = reason
                
                # Update database
                async with get_db_session() as db_session:
                    from sqlalchemy import update
                    await db_session.execute(
                        update(Call)
                        .where(Call.id == uuid.UUID(call_id))
                        .values(
                            status=CallStatus.COMPLETED,
                            ended_at=datetime.utcnow()
                        )
                    )
                    await db_session.commit()
                
                # Remove from active sessions
                del self.call_sessions[call_id]
                
        except Exception as e:
            self.logger.error("Failed to end call session", call_id=call_id, error=str(e))
    
    def _calculate_quality_score(self, packet_loss: float, jitter: float, rtt: float) -> float:
        """Calculate call quality score based on metrics."""
        # Simple quality scoring algorithm
        score = 100.0
        
        # Penalize packet loss (0-5% is acceptable)
        if packet_loss > 0.05:
            score -= (packet_loss - 0.05) * 1000
        
        # Penalize jitter (0-30ms is acceptable)
        if jitter > 30:
            score -= (jitter - 30) * 2
        
        # Penalize RTT (0-150ms is acceptable)
        if rtt > 150:
            score -= (rtt - 150) * 0.5
        
        return max(0.0, min(100.0, score))
    
    def _determine_quality_level(self, score: float) -> CallQuality:
        """Determine quality level from score."""
        if score >= 80:
            return CallQuality.EXCELLENT
        elif score >= 60:
            return CallQuality.GOOD
        elif score >= 40:
            return CallQuality.FAIR
        else:
            return CallQuality.POOR
    
    def _get_quality_recommendations(self, metrics: CallQualityMetrics) -> List[str]:
        """Get quality improvement recommendations."""
        recommendations = []
        
        if metrics.packet_loss > 0.05:
            recommendations.append("Check network connection - high packet loss detected")
        
        if metrics.jitter > 30:
            recommendations.append("Network jitter is high - consider using wired connection")
        
        if metrics.round_trip_time > 200:
            recommendations.append("High latency detected - check network routing")
        
        if metrics.bandwidth_kbps < 64:
            recommendations.append("Low bandwidth - ensure sufficient network capacity")
        
        return recommendations