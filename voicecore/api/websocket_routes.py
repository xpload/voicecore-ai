"""
WebSocket API routes for VoiceCore AI.

Provides real-time communication endpoints for agent status updates,
call notifications, and system events with proper authentication
and tenant isolation.
"""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from voicecore.services.websocket_service import websocket_manager, MessageType, WebSocketMessage
from voicecore.services.agent_service import AgentService
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils


logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])
security = HTTPBearer()


async def get_agent_service() -> AgentService:
    """Dependency to get agent service instance."""
    return AgentService()


async def authenticate_websocket_connection(
    token: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None)
) -> tuple[uuid.UUID, Optional[uuid.UUID], str]:
    """
    Authenticate WebSocket connection and extract user information.
    
    Args:
        token: Authentication token
        tenant_id: Tenant UUID string
        agent_id: Agent UUID string (optional)
        
    Returns:
        tuple: (tenant_id, agent_id, user_type)
        
    Raises:
        HTTPException: If authentication fails
    """
    # TODO: Implement proper JWT token validation
    # For now, we'll use basic validation
    
    if not token or not tenant_id:
        raise HTTPException(status_code=401, detail="Missing authentication parameters")
    
    try:
        tenant_uuid = uuid.UUID(tenant_id)
        agent_uuid = uuid.UUID(agent_id) if agent_id else None
        
        # Determine user type
        user_type = "agent" if agent_uuid else "admin"
        
        return tenant_uuid, agent_uuid, user_type
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")


@router.websocket("/agent/{tenant_id}")
async def agent_websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str,
    token: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for agent real-time communication.
    
    Handles agent status updates, call notifications, and system events
    with proper authentication and tenant isolation.
    """
    connection_id = None
    
    try:
        # Authenticate connection
        tenant_uuid, agent_uuid, user_type = await authenticate_websocket_connection(
            token=token,
            tenant_id=tenant_id,
            agent_id=agent_id
        )
        
        # Connect to WebSocket manager
        connection_id = await websocket_manager.connect(
            websocket=websocket,
            tenant_id=tenant_uuid,
            user_type=user_type,
            agent_id=agent_uuid
        )
        
        logger.info(
            "Agent WebSocket connection established",
            connection_id=connection_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            user_type=user_type
        )
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                raw_message = await websocket.receive_text()
                
                # Handle message through WebSocket manager
                await websocket_manager.handle_message(connection_id, raw_message)
                
            except WebSocketDisconnect:
                logger.info("Agent WebSocket disconnected", connection_id=connection_id)
                break
            except Exception as e:
                logger.error(
                    "Error handling agent WebSocket message",
                    connection_id=connection_id,
                    error=str(e)
                )
                # Send error message to client
                error_message = WebSocketMessage(
                    type=MessageType.ERROR,
                    data={"error": "Message processing failed"},
                    timestamp=datetime.utcnow()
                )
                await websocket_manager._send_to_connection(connection_id, error_message)
    
    except HTTPException as e:
        # Authentication failed
        await websocket.close(code=1008, reason=e.detail)
        logger.warning("Agent WebSocket authentication failed", error=e.detail)
    
    except Exception as e:
        logger.error("Agent WebSocket connection error", error=str(e))
        await websocket.close(code=1011, reason="Internal server error")
    
    finally:
        # Cleanup connection
        if connection_id:
            await websocket_manager.disconnect(connection_id)


@router.websocket("/admin/{tenant_id}")
async def admin_websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for admin/supervisor real-time communication.
    
    Provides system-wide notifications, agent monitoring, and
    administrative updates with proper authentication.
    """
    connection_id = None
    
    try:
        # Authenticate connection
        tenant_uuid, _, user_type = await authenticate_websocket_connection(
            token=token,
            tenant_id=tenant_id,
            agent_id=None
        )
        
        # Connect to WebSocket manager
        connection_id = await websocket_manager.connect(
            websocket=websocket,
            tenant_id=tenant_uuid,
            user_type="admin",
            agent_id=None
        )
        
        logger.info(
            "Admin WebSocket connection established",
            connection_id=connection_id,
            tenant_id=tenant_id,
            user_type="admin"
        )
        
        # Send initial system status
        from datetime import datetime
        initial_message = WebSocketMessage(
            type=MessageType.SYSTEM_NOTIFICATION,
            data={
                "message": "Admin dashboard connected",
                "connection_stats": websocket_manager.get_connection_stats(),
                "timestamp": datetime.utcnow().isoformat()
            },
            timestamp=datetime.utcnow()
        )
        await websocket_manager._send_to_connection(connection_id, initial_message)
        
        # Handle incoming messages
        while True:
            try:
                raw_message = await websocket.receive_text()
                await websocket_manager.handle_message(connection_id, raw_message)
                
            except WebSocketDisconnect:
                logger.info("Admin WebSocket disconnected", connection_id=connection_id)
                break
            except Exception as e:
                logger.error(
                    "Error handling admin WebSocket message",
                    connection_id=connection_id,
                    error=str(e)
                )
    
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
        logger.warning("Admin WebSocket authentication failed", error=e.detail)
    
    except Exception as e:
        logger.error("Admin WebSocket connection error", error=str(e))
        await websocket.close(code=1011, reason="Internal server error")
    
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)


@router.websocket("/system")
async def system_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    system_key: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for system-level communication.
    
    Used for internal system notifications, health monitoring,
    and cross-tenant administrative functions.
    """
    connection_id = None
    
    try:
        # Validate system authentication
        if not token or not system_key:
            raise HTTPException(status_code=401, detail="Missing system authentication")
        
        # TODO: Implement proper system key validation
        # For now, use a simple check
        if system_key != "system_internal_key":
            raise HTTPException(status_code=401, detail="Invalid system key")
        
        # Use a system tenant ID
        system_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        
        # Connect to WebSocket manager
        connection_id = await websocket_manager.connect(
            websocket=websocket,
            tenant_id=system_tenant_id,
            user_type="system",
            agent_id=None
        )
        
        logger.info("System WebSocket connection established", connection_id=connection_id)
        
        # Handle incoming messages
        while True:
            try:
                raw_message = await websocket.receive_text()
                await websocket_manager.handle_message(connection_id, raw_message)
                
            except WebSocketDisconnect:
                logger.info("System WebSocket disconnected", connection_id=connection_id)
                break
            except Exception as e:
                logger.error(
                    "Error handling system WebSocket message",
                    connection_id=connection_id,
                    error=str(e)
                )
    
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
        logger.warning("System WebSocket authentication failed", error=e.detail)
    
    except Exception as e:
        logger.error("System WebSocket connection error", error=str(e))
        await websocket.close(code=1011, reason="Internal server error")
    
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)


# HTTP endpoints for WebSocket management

@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "status": "ok",
        "stats": websocket_manager.get_connection_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/broadcast/tenant/{tenant_id}")
async def broadcast_to_tenant(
    tenant_id: str,
    message_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Broadcast message to all connections for a specific tenant.
    
    Used for administrative notifications and system-wide updates.
    """
    try:
        # TODO: Validate admin credentials
        
        tenant_uuid = uuid.UUID(tenant_id)
        
        from datetime import datetime
        message = WebSocketMessage(
            type=MessageType.SYSTEM_NOTIFICATION,
            data=message_data,
            timestamp=datetime.utcnow()
        )
        
        await websocket_manager.send_to_tenant(tenant_uuid, message)
        
        return {
            "status": "success",
            "message": "Broadcast sent",
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    except Exception as e:
        logger.error("Broadcast failed", tenant_id=tenant_id, error=str(e))
        raise HTTPException(status_code=500, detail="Broadcast failed")


@router.post("/broadcast/agent/{agent_id}")
async def broadcast_to_agent(
    agent_id: str,
    message_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Broadcast message to all connections for a specific agent.
    
    Used for agent-specific notifications and status updates.
    """
    try:
        # TODO: Validate admin credentials
        
        agent_uuid = uuid.UUID(agent_id)
        
        from datetime import datetime
        message = WebSocketMessage(
            type=MessageType.SYSTEM_NOTIFICATION,
            data=message_data,
            timestamp=datetime.utcnow()
        )
        
        await websocket_manager.send_to_agent(agent_uuid, message)
        
        return {
            "status": "success",
            "message": "Broadcast sent",
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    except Exception as e:
        logger.error("Agent broadcast failed", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail="Broadcast failed")

# WebRTC Signaling WebSocket Endpoints

@router.websocket("/webrtc/{tenant_id}")
async def webrtc_signaling_endpoint(
    websocket: WebSocket,
    tenant_id: str,
    token: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for WebRTC signaling.
    
    Handles WebRTC peer connection signaling, call setup, and quality monitoring
    for browser-based softphone functionality.
    """
    peer_id = None
    
    try:
        # Authenticate connection
        tenant_uuid, agent_uuid, user_type = await authenticate_websocket_connection(
            token=token,
            tenant_id=tenant_id,
            agent_id=agent_id
        )
        
        if not agent_uuid:
            raise HTTPException(status_code=400, detail="Agent ID required for WebRTC")
        
        # Accept WebSocket connection
        await websocket.accept()
        
        # Initialize WebRTC gateway service
        from voicecore.services.webrtc_gateway_service import WebRTCGatewayService
        webrtc_service = WebRTCGatewayService()
        
        # Create peer connection
        peer_id = await webrtc_service.create_peer_connection(
            agent_id=agent_uuid,
            tenant_id=tenant_uuid,
            websocket_connection=websocket
        )
        
        logger.info(
            "WebRTC signaling connection established",
            peer_id=peer_id,
            tenant_id=tenant_id,
            agent_id=agent_id
        )
        
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection-established",
            "peer_id": peer_id,
            "ice_servers": webrtc_service.ice_servers,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Handle signaling messages
        while True:
            try:
                # Receive message from client
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)
                
                # Process signaling message
                response = await webrtc_service.handle_signaling_message(peer_id, message)
                
                # Send response if needed
                if response:
                    await websocket.send_text(json.dumps(response))
                
            except WebSocketDisconnect:
                logger.info("WebRTC signaling disconnected", peer_id=peer_id)
                break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in WebRTC message", peer_id=peer_id)
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except Exception as e:
                logger.error(
                    "Error handling WebRTC signaling message",
                    peer_id=peer_id,
                    error=str(e)
                )
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }))
    
    except HTTPException as e:
        # Authentication failed
        await websocket.close(code=1008, reason=e.detail)
        logger.warning("WebRTC signaling authentication failed", error=e.detail)
    
    except Exception as e:
        logger.error("WebRTC signaling connection error", error=str(e))
        await websocket.close(code=1011, reason="Internal server error")
    
    finally:
        # Cleanup peer connection
        if peer_id:
            try:
                from voicecore.services.webrtc_gateway_service import WebRTCGatewayService
                webrtc_service = WebRTCGatewayService()
                await webrtc_service.disconnect_peer(peer_id, "websocket_closed")
            except Exception as e:
                logger.error("Failed to cleanup WebRTC peer", peer_id=peer_id, error=str(e))


# WebRTC Management HTTP Endpoints

@router.get("/webrtc/peers")
async def get_webrtc_peers(
    tenant_id: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get list of active WebRTC peers.
    
    Provides information about active WebRTC connections for monitoring
    and administrative purposes.
    """
    try:
        # TODO: Validate admin credentials
        
        from voicecore.services.webrtc_gateway_service import WebRTCGatewayService
        webrtc_service = WebRTCGatewayService()
        
        tenant_uuid = uuid.UUID(tenant_id) if tenant_id else None
        active_peers = await webrtc_service.get_active_peers(tenant_uuid)
        
        return {
            "status": "success",
            "peers": active_peers,
            "count": len(active_peers),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    except Exception as e:
        logger.error("Failed to get WebRTC peers", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get peers")


@router.get("/webrtc/peer/{peer_id}/status")
async def get_webrtc_peer_status(
    peer_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get status of a specific WebRTC peer.
    
    Provides detailed information about peer connection state,
    call quality metrics, and activity status.
    """
    try:
        # TODO: Validate credentials and peer access
        
        from voicecore.services.webrtc_gateway_service import WebRTCGatewayService
        webrtc_service = WebRTCGatewayService()
        
        peer_status = await webrtc_service.get_peer_status(peer_id)
        
        if not peer_status:
            raise HTTPException(status_code=404, detail="Peer not found")
        
        return {
            "status": "success",
            "peer": peer_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get peer status", peer_id=peer_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get peer status")


@router.get("/webrtc/peer/{peer_id}/quality")
async def get_webrtc_peer_quality(
    peer_id: str,
    time_range: int = Query(5, description="Time range in minutes"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get call quality metrics for a WebRTC peer.
    
    Provides detailed quality metrics including packet loss, jitter,
    RTT, and quality scores over the specified time range.
    """
    try:
        # TODO: Validate credentials and peer access
        
        from voicecore.services.webrtc_gateway_service import WebRTCGatewayService
        webrtc_service = WebRTCGatewayService()
        
        quality_metrics = await webrtc_service.get_call_quality_metrics(peer_id, time_range)
        
        return {
            "status": "success",
            "peer_id": peer_id,
            "time_range_minutes": time_range,
            "metrics": quality_metrics,
            "count": len(quality_metrics),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get quality metrics", peer_id=peer_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get quality metrics")


@router.post("/webrtc/peer/{peer_id}/disconnect")
async def disconnect_webrtc_peer(
    peer_id: str,
    reason: str = "admin_disconnect",
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Disconnect a WebRTC peer.
    
    Administratively disconnect a WebRTC peer connection,
    ending any active calls and cleaning up resources.
    """
    try:
        # TODO: Validate admin credentials
        
        from voicecore.services.webrtc_gateway_service import WebRTCGatewayService
        webrtc_service = WebRTCGatewayService()
        
        success = await webrtc_service.disconnect_peer(peer_id, reason)
        
        if not success:
            raise HTTPException(status_code=404, detail="Peer not found")
        
        return {
            "status": "success",
            "message": "Peer disconnected",
            "peer_id": peer_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disconnect peer", peer_id=peer_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to disconnect peer")


@router.post("/webrtc/call/initiate")
async def initiate_webrtc_call(
    call_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Initiate an outbound call via WebRTC.
    
    Creates a new outbound call from a WebRTC peer to a PSTN number,
    handling the integration between WebRTC and Twilio.
    """
    try:
        # TODO: Validate credentials and extract user context
        
        peer_id = call_data.get("peer_id")
        target_number = call_data.get("target_number")
        call_context = call_data.get("context", {})
        
        if not peer_id or not target_number:
            raise HTTPException(status_code=400, detail="peer_id and target_number are required")
        
        from voicecore.services.webrtc_gateway_service import WebRTCGatewayService
        webrtc_service = WebRTCGatewayService()
        
        result = await webrtc_service.initiate_outbound_call(
            peer_id=peer_id,
            target_number=target_number,
            call_context=call_context
        )
        
        return {
            "status": "success",
            "call": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to initiate WebRTC call", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to initiate call")


# Import json for WebRTC signaling
import json