"""
Progressive Web App (PWA) service for VoiceCore AI.

Provides PWA functionality including push notifications, offline capabilities,
and mobile-optimized features for agent applications.
"""

import uuid
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import Agent, Call, CallStatus
from voicecore.logging import get_logger
from voicecore.config import settings


logger = get_logger(__name__)


@dataclass
class PushSubscription:
    """Represents a push notification subscription."""
    endpoint: str
    keys: Dict[str, str]
    agent_id: uuid.UUID
    tenant_id: uuid.UUID
    user_agent: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["agent_id"] = str(self.agent_id)
        data["tenant_id"] = str(self.tenant_id)
        data["created_at"] = self.created_at.isoformat()
        if self.last_used:
            data["last_used"] = self.last_used.isoformat()
        return data


@dataclass
class NotificationPayload:
    """Represents a push notification payload."""
    title: str
    body: str
    icon: Optional[str] = None
    badge: Optional[str] = None
    tag: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, str]]] = None
    require_interaction: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class PWAServiceError(Exception):
    """Base exception for PWA service errors."""
    pass


class InvalidSubscriptionError(PWAServiceError):
    """Raised when a push subscription is invalid."""
    pass


class NotificationDeliveryError(PWAServiceError):
    """Raised when notification delivery fails."""
    pass


class PWAService:
    """
    Progressive Web App service for mobile agent functionality.
    
    Handles push notifications, offline capabilities, background sync,
    and mobile-optimized features for the agent application.
    """
    
    def __init__(self):
        self.logger = logger
        self.subscriptions: Dict[str, PushSubscription] = {}
        self.notification_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # VAPID keys for push notifications (should be configured in settings)
        self.vapid_public_key = getattr(settings, 'vapid_public_key', '')
        self.vapid_private_key = getattr(settings, 'vapid_private_key', '')
        self.vapid_email = getattr(settings, 'vapid_email', 'admin@voicecore.ai')
    
    async def register_push_subscription(
        self,
        agent_id: uuid.UUID,
        tenant_id: uuid.UUID,
        subscription_data: Dict[str, Any],
        user_agent: str
    ) -> str:
        """
        Register a push notification subscription for an agent.
        
        Args:
            agent_id: Agent UUID
            tenant_id: Tenant UUID
            subscription_data: Push subscription data from browser
            user_agent: User agent string
            
        Returns:
            str: Subscription ID
            
        Raises:
            InvalidSubscriptionError: If subscription data is invalid
        """
        try:
            # Validate subscription data
            if not subscription_data.get('endpoint'):
                raise InvalidSubscriptionError("Missing endpoint in subscription")
            
            if not subscription_data.get('keys'):
                raise InvalidSubscriptionError("Missing keys in subscription")
            
            required_keys = ['p256dh', 'auth']
            for key in required_keys:
                if key not in subscription_data['keys']:
                    raise InvalidSubscriptionError(f"Missing key: {key}")
            
            # Verify agent exists
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
                    raise InvalidSubscriptionError(f"Agent {agent_id} not found or inactive")
            
            # Create subscription
            subscription_id = f"sub_{uuid.uuid4().hex[:16]}"
            
            subscription = PushSubscription(
                endpoint=subscription_data['endpoint'],
                keys=subscription_data['keys'],
                agent_id=agent_id,
                tenant_id=tenant_id,
                user_agent=user_agent,
                created_at=datetime.utcnow()
            )
            
            # Store subscription
            self.subscriptions[subscription_id] = subscription
            self.notification_history[subscription_id] = []
            
            # Remove old subscriptions for the same agent
            await self._cleanup_old_subscriptions(agent_id, subscription_id)
            
            self.logger.info(
                "Push subscription registered",
                subscription_id=subscription_id,
                agent_id=str(agent_id),
                tenant_id=str(tenant_id),
                endpoint=subscription_data['endpoint'][:50] + "..."
            )
            
            return subscription_id
            
        except InvalidSubscriptionError:
            raise
        except Exception as e:
            self.logger.error("Failed to register push subscription", error=str(e))
            raise PWAServiceError(f"Failed to register subscription: {str(e)}")
    
    async def send_push_notification(
        self,
        agent_id: uuid.UUID,
        notification: NotificationPayload
    ) -> bool:
        """
        Send push notification to an agent.
        
        Args:
            agent_id: Agent UUID
            notification: Notification payload
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Find active subscriptions for agent
            agent_subscriptions = [
                (sub_id, sub) for sub_id, sub in self.subscriptions.items()
                if sub.agent_id == agent_id and sub.is_active
            ]
            
            if not agent_subscriptions:
                self.logger.warning(
                    "No active push subscriptions found for agent",
                    agent_id=str(agent_id)
                )
                return False
            
            success_count = 0
            
            for subscription_id, subscription in agent_subscriptions:
                try:
                    # Send notification using web push
                    await self._send_web_push(subscription, notification)
                    
                    # Update subscription last used
                    subscription.last_used = datetime.utcnow()
                    
                    # Store in notification history
                    self.notification_history[subscription_id].append({
                        "notification": notification.to_dict(),
                        "sent_at": datetime.utcnow().isoformat(),
                        "status": "sent"
                    })
                    
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to send push notification to subscription",
                        subscription_id=subscription_id,
                        error=str(e)
                    )
                    
                    # Mark subscription as inactive if it's invalid
                    if "invalid" in str(e).lower() or "expired" in str(e).lower():
                        subscription.is_active = False
                    
                    # Store failed notification
                    self.notification_history[subscription_id].append({
                        "notification": notification.to_dict(),
                        "sent_at": datetime.utcnow().isoformat(),
                        "status": "failed",
                        "error": str(e)
                    })
            
            self.logger.info(
                "Push notification sent",
                agent_id=str(agent_id),
                success_count=success_count,
                total_subscriptions=len(agent_subscriptions),
                notification_title=notification.title
            )
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error("Failed to send push notification", agent_id=str(agent_id), error=str(e))
            return False
    
    async def send_incoming_call_notification(
        self,
        agent_id: uuid.UUID,
        call_id: uuid.UUID,
        caller_number: str,
        caller_name: Optional[str] = None
    ) -> bool:
        """
        Send incoming call notification to agent.
        
        Args:
            agent_id: Agent UUID
            call_id: Call UUID
            caller_number: Caller's phone number
            caller_name: Caller's name (optional)
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            caller_display = caller_name or caller_number
            
            notification = NotificationPayload(
                title="Incoming Call",
                body=f"Call from {caller_display}",
                icon="/static/icons/call-192x192.png",
                badge="/static/icons/badge-72x72.png",
                tag="incoming-call",
                require_interaction=True,
                data={
                    "type": "incoming_call",
                    "call_id": str(call_id),
                    "caller_number": caller_number,
                    "caller_name": caller_name,
                    "timestamp": datetime.utcnow().isoformat()
                },
                actions=[
                    {
                        "action": "answer",
                        "title": "Answer",
                        "icon": "/static/icons/answer-32x32.png"
                    },
                    {
                        "action": "decline",
                        "title": "Decline",
                        "icon": "/static/icons/decline-32x32.png"
                    }
                ]
            )
            
            return await self.send_push_notification(agent_id, notification)
            
        except Exception as e:
            self.logger.error("Failed to send incoming call notification", error=str(e))
            return False
    
    async def send_status_update_notification(
        self,
        agent_id: uuid.UUID,
        message: str,
        status_type: str = "info"
    ) -> bool:
        """
        Send status update notification to agent.
        
        Args:
            agent_id: Agent UUID
            message: Status message
            status_type: Type of status (info, warning, error)
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            icon_map = {
                "info": "/static/icons/info-192x192.png",
                "warning": "/static/icons/warning-192x192.png",
                "error": "/static/icons/error-192x192.png"
            }
            
            notification = NotificationPayload(
                title="Status Update",
                body=message,
                icon=icon_map.get(status_type, icon_map["info"]),
                badge="/static/icons/badge-72x72.png",
                tag="status-update",
                require_interaction=status_type == "error",
                data={
                    "type": "status_update",
                    "status_type": status_type,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            return await self.send_push_notification(agent_id, notification)
            
        except Exception as e:
            self.logger.error("Failed to send status update notification", error=str(e))
            return False
    
    async def send_system_alert_notification(
        self,
        agent_id: uuid.UUID,
        alert_message: str,
        alert_level: str = "warning"
    ) -> bool:
        """
        Send system alert notification to agent.
        
        Args:
            agent_id: Agent UUID
            alert_message: Alert message
            alert_level: Alert level (info, warning, critical)
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            notification = NotificationPayload(
                title="System Alert",
                body=alert_message,
                icon="/static/icons/alert-192x192.png",
                badge="/static/icons/badge-72x72.png",
                tag="system-alert",
                require_interaction=alert_level == "critical",
                data={
                    "type": "system_alert",
                    "alert_level": alert_level,
                    "message": alert_message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            return await self.send_push_notification(agent_id, notification)
            
        except Exception as e:
            self.logger.error("Failed to send system alert notification", error=str(e))
            return False
    
    async def unregister_push_subscription(
        self,
        subscription_id: str
    ) -> bool:
        """
        Unregister a push notification subscription.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            bool: True if unregistered successfully
        """
        try:
            if subscription_id in self.subscriptions:
                subscription = self.subscriptions[subscription_id]
                
                # Mark as inactive
                subscription.is_active = False
                
                self.logger.info(
                    "Push subscription unregistered",
                    subscription_id=subscription_id,
                    agent_id=str(subscription.agent_id)
                )
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to unregister subscription", subscription_id=subscription_id, error=str(e))
            return False
    
    async def get_agent_subscriptions(
        self,
        agent_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all subscriptions for an agent.
        
        Args:
            agent_id: Agent UUID
            
        Returns:
            List[Dict[str, Any]]: List of subscriptions
        """
        try:
            agent_subscriptions = []
            
            for sub_id, subscription in self.subscriptions.items():
                if subscription.agent_id == agent_id:
                    sub_data = subscription.to_dict()
                    sub_data["subscription_id"] = sub_id
                    sub_data["notification_count"] = len(self.notification_history.get(sub_id, []))
                    agent_subscriptions.append(sub_data)
            
            return agent_subscriptions
            
        except Exception as e:
            self.logger.error("Failed to get agent subscriptions", agent_id=str(agent_id), error=str(e))
            return []
    
    async def get_notification_history(
        self,
        subscription_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get notification history for a subscription.
        
        Args:
            subscription_id: Subscription ID
            limit: Maximum number of notifications to return
            
        Returns:
            List[Dict[str, Any]]: Notification history
        """
        try:
            if subscription_id not in self.notification_history:
                return []
            
            history = self.notification_history[subscription_id]
            
            # Return most recent notifications
            return history[-limit:] if len(history) > limit else history
            
        except Exception as e:
            self.logger.error("Failed to get notification history", subscription_id=subscription_id, error=str(e))
            return []
    
    async def cleanup_inactive_subscriptions(self, max_age_days: int = 30) -> int:
        """
        Clean up inactive or old subscriptions.
        
        Args:
            max_age_days: Maximum age in days for inactive subscriptions
            
        Returns:
            int: Number of subscriptions cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            cleaned_count = 0
            
            subscriptions_to_remove = []
            
            for sub_id, subscription in self.subscriptions.items():
                should_remove = False
                
                # Remove inactive subscriptions
                if not subscription.is_active:
                    should_remove = True
                
                # Remove old unused subscriptions
                elif (subscription.last_used is None and 
                      subscription.created_at < cutoff_date):
                    should_remove = True
                
                # Remove subscriptions not used recently
                elif (subscription.last_used and 
                      subscription.last_used < cutoff_date):
                    should_remove = True
                
                if should_remove:
                    subscriptions_to_remove.append(sub_id)
            
            # Remove subscriptions
            for sub_id in subscriptions_to_remove:
                del self.subscriptions[sub_id]
                if sub_id in self.notification_history:
                    del self.notification_history[sub_id]
                cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(
                    "Cleaned up inactive push subscriptions",
                    cleaned_count=cleaned_count,
                    max_age_days=max_age_days
                )
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error("Failed to cleanup subscriptions", error=str(e))
            return 0
    
    def get_vapid_public_key(self) -> str:
        """
        Get VAPID public key for client-side subscription.
        
        Returns:
            str: VAPID public key
        """
        return self.vapid_public_key
    
    async def get_pwa_config(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get PWA configuration for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Dict[str, Any]: PWA configuration
        """
        try:
            # Get tenant-specific settings
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # TODO: Get tenant-specific PWA settings from database
                # For now, return default configuration
                
                config = {
                    "vapid_public_key": self.vapid_public_key,
                    "notification_settings": {
                        "incoming_calls": True,
                        "status_updates": True,
                        "system_alerts": True
                    },
                    "offline_capabilities": {
                        "cache_duration_hours": 24,
                        "sync_interval_minutes": 15,
                        "max_offline_actions": 100
                    },
                    "features": {
                        "background_sync": True,
                        "push_notifications": True,
                        "offline_mode": True,
                        "call_recording": True
                    }
                }
                
                return config
                
        except Exception as e:
            self.logger.error("Failed to get PWA config", tenant_id=str(tenant_id), error=str(e))
            return {}
    
    # Private helper methods
    
    async def _send_web_push(
        self,
        subscription: PushSubscription,
        notification: NotificationPayload
    ):
        """Send web push notification using pywebpush."""
        try:
            # This would use the pywebpush library in a real implementation
            # For now, we'll simulate the push notification
            
            payload = json.dumps(notification.to_dict())
            
            # Simulate web push (in real implementation, use pywebpush)
            self.logger.debug(
                "Simulating web push notification",
                endpoint=subscription.endpoint[:50] + "...",
                payload_size=len(payload),
                notification_title=notification.title
            )
            
            # In real implementation:
            # from pywebpush import webpush
            # webpush(
            #     subscription_info={
            #         "endpoint": subscription.endpoint,
            #         "keys": subscription.keys
            #     },
            #     data=payload,
            #     vapid_private_key=self.vapid_private_key,
            #     vapid_claims={
            #         "sub": f"mailto:{self.vapid_email}"
            #     }
            # )
            
        except Exception as e:
            self.logger.error("Web push failed", error=str(e))
            raise NotificationDeliveryError(f"Web push failed: {str(e)}")
    
    async def _cleanup_old_subscriptions(
        self,
        agent_id: uuid.UUID,
        keep_subscription_id: str
    ):
        """Clean up old subscriptions for an agent."""
        try:
            subscriptions_to_remove = []
            
            for sub_id, subscription in self.subscriptions.items():
                if (subscription.agent_id == agent_id and 
                    sub_id != keep_subscription_id):
                    subscriptions_to_remove.append(sub_id)
            
            for sub_id in subscriptions_to_remove:
                del self.subscriptions[sub_id]
                if sub_id in self.notification_history:
                    del self.notification_history[sub_id]
            
            if subscriptions_to_remove:
                self.logger.info(
                    "Cleaned up old subscriptions for agent",
                    agent_id=str(agent_id),
                    removed_count=len(subscriptions_to_remove)
                )
                
        except Exception as e:
            self.logger.error("Failed to cleanup old subscriptions", error=str(e))