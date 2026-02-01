"""
PWA API routes for VoiceCore AI.

Provides Progressive Web App functionality including push notifications,
offline capabilities, and mobile-optimized features for agent applications.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from voicecore.services.pwa_service import PWAService, PWAServiceError, InvalidSubscriptionError
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils


logger = get_logger(__name__)
router = APIRouter(prefix="/pwa", tags=["PWA"])
security = HTTPBearer()


# Pydantic models for request/response
class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: Dict[str, str]
    agent_id: str
    tenant_id: str


class NotificationRequest(BaseModel):
    agent_id: str
    title: str
    body: str
    icon: Optional[str] = None
    tag: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    require_interaction: bool = False


class CallNotificationRequest(BaseModel):
    agent_id: str
    call_id: str
    caller_number: str
    caller_name: Optional[str] = None


# Dependency for getting PWA service
def get_pwa_service() -> PWAService:
    """Dependency to get PWA service instance."""
    return PWAService()


# PWA Manifest and Service Worker endpoints

@router.get("/manifest.json")
async def get_pwa_manifest():
    """
    Get PWA manifest file.
    
    Returns the Progressive Web App manifest with app metadata,
    icons, and configuration for installation.
    """
    try:
        return FileResponse(
            path="voicecore/static/manifest.json",
            media_type="application/json",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Manifest not found")


@router.get("/sw.js")
async def get_service_worker():
    """
    Get service worker JavaScript file.
    
    Returns the service worker script for offline functionality,
    push notifications, and background sync.
    """
    try:
        return FileResponse(
            path="voicecore/static/sw.js",
            media_type="application/javascript",
            headers={
                "Cache-Control": "public, max-age=0",  # Don't cache service worker
                "Access-Control-Allow-Origin": "*"
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Service worker not found")


# Push Notification endpoints

@router.post("/push/subscribe")
async def subscribe_to_push_notifications(
    subscription_data: PushSubscriptionRequest,
    request: Request,
    pwa_service: PWAService = Depends(get_pwa_service)
):
    """
    Subscribe to push notifications.
    
    Registers a push notification subscription for an agent,
    enabling real-time notifications for calls and system events.
    """
    try:
        # TODO: Validate authentication and authorization
        
        agent_uuid = uuid.UUID(subscription_data.agent_id)
        tenant_uuid = uuid.UUID(subscription_data.tenant_id)
        user_agent = request.headers.get("User-Agent", "Unknown")
        
        subscription_id = await pwa_service.register_push_subscription(
            agent_id=agent_uuid,
            tenant_id=tenant_uuid,
            subscription_data={
                "endpoint": subscription_data.endpoint,
                "keys": subscription_data.keys
            },
            user_agent=user_agent
        )
        
        return {
            "status": "success",
            "subscription_id": subscription_id,
            "message": "Push subscription registered successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except InvalidSubscriptionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PWAServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Push subscription failed", error=str(e))
        raise HTTPException(status_code=500, detail="Subscription failed")


@router.delete("/push/subscribe/{subscription_id}")
async def unsubscribe_from_push_notifications(
    subscription_id: str,
    pwa_service: PWAService = Depends(get_pwa_service),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Unsubscribe from push notifications.
    
    Removes a push notification subscription, stopping notifications
    for the associated device/browser.
    """
    try:
        # TODO: Validate authentication and subscription ownership
        
        success = await pwa_service.unregister_push_subscription(subscription_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {
            "status": "success",
            "message": "Push subscription removed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Push unsubscription failed", subscription_id=subscription_id, error=str(e))
        raise HTTPException(status_code=500, detail="Unsubscription failed")


@router.post("/push/send")
async def send_push_notification(
    notification_data: NotificationRequest,
    pwa_service: PWAService = Depends(get_pwa_service),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Send push notification to an agent.
    
    Sends a custom push notification to all active subscriptions
    for the specified agent.
    """
    try:
        # TODO: Validate admin authentication
        
        agent_uuid = uuid.UUID(notification_data.agent_id)
        
        from voicecore.services.pwa_service import NotificationPayload
        
        notification = NotificationPayload(
            title=notification_data.title,
            body=notification_data.body,
            icon=notification_data.icon,
            tag=notification_data.tag,
            data=notification_data.data,
            require_interaction=notification_data.require_interaction
        )
        
        success = await pwa_service.send_push_notification(agent_uuid, notification)
        
        return {
            "status": "success" if success else "partial",
            "message": "Notification sent" if success else "Some notifications failed",
            "agent_id": notification_data.agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    except Exception as e:
        logger.error("Push notification send failed", error=str(e))
        raise HTTPException(status_code=500, detail="Notification send failed")


@router.post("/push/call")
async def send_call_notification(
    call_data: CallNotificationRequest,
    pwa_service: PWAService = Depends(get_pwa_service),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Send incoming call notification.
    
    Sends a specialized push notification for incoming calls
    with call-specific actions (answer/decline).
    """
    try:
        # TODO: Validate system authentication
        
        agent_uuid = uuid.UUID(call_data.agent_id)
        call_uuid = uuid.UUID(call_data.call_id)
        
        success = await pwa_service.send_incoming_call_notification(
            agent_id=agent_uuid,
            call_id=call_uuid,
            caller_number=call_data.caller_number,
            caller_name=call_data.caller_name
        )
        
        return {
            "status": "success" if success else "failed",
            "message": "Call notification sent" if success else "Call notification failed",
            "call_id": call_data.call_id,
            "agent_id": call_data.agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except Exception as e:
        logger.error("Call notification failed", error=str(e))
        raise HTTPException(status_code=500, detail="Call notification failed")


# PWA Configuration endpoints

@router.get("/config/{tenant_id}")
async def get_pwa_config(
    tenant_id: str,
    pwa_service: PWAService = Depends(get_pwa_service),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get PWA configuration for a tenant.
    
    Returns PWA-specific configuration including VAPID keys,
    notification settings, and feature flags.
    """
    try:
        # TODO: Validate tenant access
        
        tenant_uuid = uuid.UUID(tenant_id)
        config = await pwa_service.get_pwa_config(tenant_uuid)
        
        return {
            "status": "success",
            "config": config,
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    except Exception as e:
        logger.error("PWA config retrieval failed", tenant_id=tenant_id, error=str(e))
        raise HTTPException(status_code=500, detail="Config retrieval failed")


@router.get("/vapid-key")
async def get_vapid_public_key(
    pwa_service: PWAService = Depends(get_pwa_service)
):
    """
    Get VAPID public key for push subscriptions.
    
    Returns the VAPID public key needed for client-side
    push notification subscriptions.
    """
    try:
        public_key = pwa_service.get_vapid_public_key()
        
        if not public_key:
            raise HTTPException(status_code=503, detail="VAPID not configured")
        
        return {
            "status": "success",
            "vapid_public_key": public_key,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("VAPID key retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="VAPID key retrieval failed")


# Subscription Management endpoints

@router.get("/subscriptions/agent/{agent_id}")
async def get_agent_subscriptions(
    agent_id: str,
    pwa_service: PWAService = Depends(get_pwa_service),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get all push subscriptions for an agent.
    
    Returns a list of active push notification subscriptions
    for the specified agent.
    """
    try:
        # TODO: Validate agent access
        
        agent_uuid = uuid.UUID(agent_id)
        subscriptions = await pwa_service.get_agent_subscriptions(agent_uuid)
        
        return {
            "status": "success",
            "subscriptions": subscriptions,
            "count": len(subscriptions),
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    except Exception as e:
        logger.error("Subscription retrieval failed", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail="Subscription retrieval failed")


@router.get("/notifications/history/{subscription_id}")
async def get_notification_history(
    subscription_id: str,
    limit: int = 50,
    pwa_service: PWAService = Depends(get_pwa_service),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get notification history for a subscription.
    
    Returns the history of push notifications sent to
    a specific subscription.
    """
    try:
        # TODO: Validate subscription access
        
        history = await pwa_service.get_notification_history(subscription_id, limit)
        
        return {
            "status": "success",
            "history": history,
            "count": len(history),
            "subscription_id": subscription_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Notification history retrieval failed", subscription_id=subscription_id, error=str(e))
        raise HTTPException(status_code=500, detail="History retrieval failed")


# Offline Support endpoints

@router.post("/offline/sync")
async def trigger_background_sync(
    sync_data: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Trigger background sync for offline actions.
    
    Processes queued offline actions when the device
    comes back online.
    """
    try:
        # TODO: Implement background sync processing
        
        sync_type = sync_data.get("type", "general")
        actions = sync_data.get("actions", [])
        
        logger.info(
            "Background sync triggered",
            sync_type=sync_type,
            action_count=len(actions)
        )
        
        # Process sync actions
        processed_count = 0
        failed_count = 0
        
        for action in actions:
            try:
                # TODO: Process individual sync action
                processed_count += 1
            except Exception as e:
                logger.error("Sync action failed", action=action, error=str(e))
                failed_count += 1
        
        return {
            "status": "success",
            "processed": processed_count,
            "failed": failed_count,
            "sync_type": sync_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Background sync failed", error=str(e))
        raise HTTPException(status_code=500, detail="Background sync failed")


@router.get("/offline/status")
async def get_offline_status():
    """
    Get offline capability status.
    
    Returns information about offline features,
    cached data, and sync status.
    """
    try:
        # TODO: Implement offline status checking
        
        status = {
            "offline_capable": True,
            "cache_status": "active",
            "last_sync": datetime.utcnow().isoformat(),
            "pending_actions": 0,
            "features": {
                "background_sync": True,
                "push_notifications": True,
                "offline_storage": True
            }
        }
        
        return {
            "status": "success",
            "offline_status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Offline status check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Offline status check failed")


# Installation and Update endpoints

@router.post("/install")
async def handle_pwa_install(
    install_data: Dict[str, Any],
    request: Request
):
    """
    Handle PWA installation event.
    
    Tracks PWA installations and provides installation
    analytics and user onboarding.
    """
    try:
        user_agent = request.headers.get("User-Agent", "Unknown")
        client_ip = SecurityUtils.get_client_ip(request)
        
        # TODO: Store installation analytics (without storing IP)
        
        logger.info(
            "PWA installation tracked",
            platform=install_data.get("platform", "unknown"),
            user_agent=user_agent[:100],  # Truncate for privacy
            timestamp=datetime.utcnow().isoformat()
        )
        
        return {
            "status": "success",
            "message": "Installation tracked",
            "onboarding_url": "/agent/onboarding",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("PWA install tracking failed", error=str(e))
        raise HTTPException(status_code=500, detail="Install tracking failed")


@router.post("/update")
async def handle_pwa_update(
    update_data: Dict[str, Any]
):
    """
    Handle PWA update event.
    
    Manages PWA updates, cache invalidation,
    and user notifications about new versions.
    """
    try:
        current_version = update_data.get("current_version", "unknown")
        new_version = update_data.get("new_version", "unknown")
        
        logger.info(
            "PWA update tracked",
            current_version=current_version,
            new_version=new_version,
            timestamp=datetime.utcnow().isoformat()
        )
        
        return {
            "status": "success",
            "message": "Update processed",
            "reload_required": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("PWA update handling failed", error=str(e))
        raise HTTPException(status_code=500, detail="Update handling failed")


# Maintenance endpoints

@router.post("/maintenance/cleanup")
async def cleanup_pwa_data(
    cleanup_data: Dict[str, Any],
    pwa_service: PWAService = Depends(get_pwa_service),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Clean up PWA data and subscriptions.
    
    Removes inactive subscriptions, old notification history,
    and expired cached data.
    """
    try:
        # TODO: Validate admin authentication
        
        max_age_days = cleanup_data.get("max_age_days", 30)
        
        cleaned_count = await pwa_service.cleanup_inactive_subscriptions(max_age_days)
        
        return {
            "status": "success",
            "message": "Cleanup completed",
            "cleaned_subscriptions": cleaned_count,
            "max_age_days": max_age_days,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("PWA cleanup failed", error=str(e))
        raise HTTPException(status_code=500, detail="Cleanup failed")