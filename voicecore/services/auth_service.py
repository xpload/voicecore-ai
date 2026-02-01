"""
Authentication and authorization service for VoiceCore AI.

Implements comprehensive API security including authentication,
authorization, JWT token management, and role-based access control
per Requirements 10.5 and 10.2.
"""

import uuid
import jwt
import bcrypt
import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models.base import BaseModel, TimestampMixin, TenantMixin
from voicecore.services.privacy_service import PrivacyService, AuditEventType
from voicecore.utils.security import SecurityUtils
from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class UserRole(Enum):
    """User roles for role-based access control."""
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    READONLY = "readonly"
    API_USER = "api_user"


class Permission(Enum):
    """System permissions."""
    # Call management
    CALL_VIEW = "call:view"
    CALL_CREATE = "call:create"
    CALL_UPDATE = "call:update"
    CALL_DELETE = "call:delete"
    
    # Agent management
    AGENT_VIEW = "agent:view"
    AGENT_CREATE = "agent:create"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    
    # Analytics
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"
    
    # Administration
    ADMIN_SYSTEM = "admin:system"
    ADMIN_TENANT = "admin:tenant"
    ADMIN_USERS = "admin:users"
    
    # API access
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"


class ApiKey(BaseModel, TimestampMixin, TenantMixin):
    """API key model for API authentication."""
    
    # Key identification
    key_id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        nullable=False,
        unique=True,
        doc="Unique key identifier"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Human-readable key name"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Key description and purpose"
    )
    
    # Key data (hashed)
    key_hash = Column(
        String(255),
        nullable=False,
        doc="Hashed API key"
    )
    
    key_prefix = Column(
        String(10),
        nullable=False,
        doc="Key prefix for identification"
    )
    
    # Permissions and access
    permissions = Column(
        JSON,
        default=list,
        nullable=False,
        doc="List of permissions granted to this key"
    )
    
    scopes = Column(
        JSON,
        default=list,
        nullable=False,
        doc="API scopes accessible with this key"
    )
    
    # Usage tracking
    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the key was last used"
    )
    
    usage_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of times key has been used"
    )
    
    # Rate limiting
    rate_limit_per_minute = Column(
        Integer,
        default=100,
        nullable=False,
        doc="Rate limit for this key (requests per minute)"
    )
    
    # Key lifecycle
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the key is active"
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the key expires"
    )
    
    created_by = Column(
        String(255),
        nullable=True,
        doc="User who created this key"
    )
    
    def __repr__(self) -> str:
        return f"<ApiKey(key_id={self.key_id}, name='{self.name}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class UserSession(BaseModel, TimestampMixin, TenantMixin):
    """User session model for session management."""
    
    session_id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        nullable=False,
        unique=True,
        doc="Unique session identifier"
    )
    
    user_id = Column(
        String(255),
        nullable=False,
        doc="User identifier (hashed for privacy)"
    )
    
    # Session data
    session_data = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Encrypted session data"
    )
    
    # Security tracking
    user_agent = Column(
        String(500),
        nullable=True,
        doc="User agent string (sanitized)"
    )
    
    # Session lifecycle
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the session expires"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the session is active"
    )
    
    last_activity_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Last activity timestamp"
    )
    
    def __repr__(self) -> str:
        return f"<UserSession(session_id={self.session_id}, user_id='{self.user_id}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the session is expired."""
        return datetime.utcnow() > self.expires_at


class AuthService:
    """
    Authentication and authorization service.
    
    Implements comprehensive API security per Requirements 10.5 and 10.2.
    """
    
    def __init__(self):
        self.logger = logger
        self.privacy_service = PrivacyService()
        self.security_utils = SecurityUtils()
        
        # JWT configuration
        self.jwt_secret = settings.JWT_SECRET_KEY
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24
        
        # Role permissions mapping
        self.role_permissions = {
            UserRole.SUPER_ADMIN: [p for p in Permission],  # All permissions
            UserRole.TENANT_ADMIN: [
                Permission.CALL_VIEW, Permission.CALL_CREATE, Permission.CALL_UPDATE,
                Permission.AGENT_VIEW, Permission.AGENT_CREATE, Permission.AGENT_UPDATE,
                Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
                Permission.ADMIN_TENANT, Permission.ADMIN_USERS,
                Permission.API_READ, Permission.API_WRITE
            ],
            UserRole.SUPERVISOR: [
                Permission.CALL_VIEW, Permission.CALL_UPDATE,
                Permission.AGENT_VIEW, Permission.AGENT_UPDATE,
                Permission.ANALYTICS_VIEW,
                Permission.API_READ
            ],
            UserRole.AGENT: [
                Permission.CALL_VIEW, Permission.CALL_UPDATE,
                Permission.AGENT_VIEW,
                Permission.API_READ
            ],
            UserRole.READONLY: [
                Permission.CALL_VIEW,
                Permission.AGENT_VIEW,
                Permission.ANALYTICS_VIEW,
                Permission.API_READ
            ],
            UserRole.API_USER: [
                Permission.API_READ, Permission.API_WRITE
            ]
        }
    
    async def create_api_key(
        self,
        tenant_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[List[Permission]] = None,
        scopes: Optional[List[str]] = None,
        rate_limit_per_minute: int = 100,
        expires_in_days: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new API key.
        
        Args:
            tenant_id: Tenant UUID
            name: Human-readable key name
            description: Key description
            permissions: List of permissions to grant
            scopes: API scopes
            rate_limit_per_minute: Rate limit for the key
            expires_in_days: Days until expiration
            created_by: User creating the key
            
        Returns:
            Dict containing the new API key and metadata
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Generate API key
                api_key = self.security_utils.generate_api_key()
                key_prefix = api_key[:8]
                key_hash = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()
                
                # Set expiration
                expires_at = None
                if expires_in_days:
                    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
                
                # Create API key record
                api_key_record = ApiKey(
                    tenant_id=tenant_id,
                    name=name,
                    description=description,
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    permissions=[p.value for p in (permissions or [])],
                    scopes=scopes or [],
                    rate_limit_per_minute=rate_limit_per_minute,
                    expires_at=expires_at,
                    created_by=created_by
                )
                
                session.add(api_key_record)
                await session.commit()
                
                # Log key creation
                await self.privacy_service.log_audit_event(
                    tenant_id=tenant_id,
                    event_type=AuditEventType.SYSTEM_CONFIGURATION,
                    action="api_key_created",
                    user_id=created_by,
                    resource=f"api_key:{api_key_record.key_id}",
                    event_data={
                        "key_name": name,
                        "permissions_count": len(permissions or []),
                        "rate_limit": rate_limit_per_minute,
                        "expires_at": expires_at.isoformat() if expires_at else None
                    },
                    success=True
                )
                
                return {
                    "key_id": str(api_key_record.key_id),
                    "api_key": api_key,  # Only returned once
                    "name": name,
                    "key_prefix": key_prefix,
                    "permissions": api_key_record.permissions,
                    "scopes": api_key_record.scopes,
                    "rate_limit_per_minute": rate_limit_per_minute,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "created_at": api_key_record.created_at.isoformat()
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to create API key",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def validate_api_key(
        self,
        tenant_id: uuid.UUID,
        api_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return key information.
        
        Args:
            tenant_id: Tenant UUID
            api_key: API key to validate
            
        Returns:
            Dict with key information if valid, None if invalid
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get key prefix
                key_prefix = api_key[:8]
                
                # Find API key by prefix
                from sqlalchemy import select
                result = await session.execute(
                    select(ApiKey).where(
                        ApiKey.tenant_id == tenant_id,
                        ApiKey.key_prefix == key_prefix,
                        ApiKey.is_active == True
                    )
                )
                api_key_record = result.scalar_one_or_none()
                
                if not api_key_record:
                    return None
                
                # Check if expired
                if api_key_record.is_expired:
                    return None
                
                # Verify key hash
                if not bcrypt.checkpw(api_key.encode(), api_key_record.key_hash.encode()):
                    return None
                
                # Update usage statistics
                api_key_record.last_used_at = datetime.utcnow()
                api_key_record.usage_count += 1
                await session.commit()
                
                # Log key usage
                await self.privacy_service.log_audit_event(
                    tenant_id=tenant_id,
                    event_type=AuditEventType.DATA_ACCESS,
                    action="api_key_used",
                    resource=f"api_key:{api_key_record.key_id}",
                    event_data={
                        "key_name": api_key_record.name,
                        "usage_count": api_key_record.usage_count
                    },
                    success=True
                )
                
                return {
                    "key_id": str(api_key_record.key_id),
                    "name": api_key_record.name,
                    "permissions": api_key_record.permissions,
                    "scopes": api_key_record.scopes,
                    "rate_limit_per_minute": api_key_record.rate_limit_per_minute,
                    "usage_count": api_key_record.usage_count,
                    "last_used_at": api_key_record.last_used_at.isoformat()
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to validate API key",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return None
    
    async def create_jwt_token(
        self,
        tenant_id: uuid.UUID,
        user_id: str,
        role: UserRole,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a JWT token for user authentication.
        
        Args:
            tenant_id: Tenant UUID
            user_id: User identifier
            role: User role
            additional_claims: Additional JWT claims
            
        Returns:
            JWT token string
        """
        try:
            now = datetime.utcnow()
            expiration = now + timedelta(hours=self.jwt_expiration_hours)
            
            # Build JWT payload
            payload = {
                "sub": user_id,  # Subject (user ID)
                "tenant_id": str(tenant_id),
                "role": role.value,
                "permissions": [p.value for p in self.role_permissions.get(role, [])],
                "iat": now,  # Issued at
                "exp": expiration,  # Expiration
                "jti": str(uuid.uuid4())  # JWT ID
            }
            
            # Add additional claims
            if additional_claims:
                payload.update(additional_claims)
            
            # Generate token
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            # Log token creation
            await self.privacy_service.log_audit_event(
                tenant_id=tenant_id,
                event_type=AuditEventType.USER_LOGIN,
                action="jwt_token_created",
                user_id=user_id,
                event_data={
                    "role": role.value,
                    "expires_at": expiration.isoformat(),
                    "permissions_count": len(self.role_permissions.get(role, []))
                },
                success=True
            )
            
            return token
            
        except Exception as e:
            self.logger.error(
                "Failed to create JWT token",
                tenant_id=str(tenant_id),
                user_id=user_id,
                error=str(e)
            )
            raise
    
    async def validate_jwt_token(
        self,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a JWT token and return claims.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Dict with token claims if valid, None if invalid
        """
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            # Extract claims
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            role = payload.get("role")
            permissions = payload.get("permissions", [])
            
            if not all([user_id, tenant_id, role]):
                return None
            
            return {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "role": role,
                "permissions": permissions,
                "expires_at": datetime.fromtimestamp(payload["exp"]).isoformat(),
                "jwt_id": payload.get("jti")
            }
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning("Invalid JWT token", error=str(e))
            return None
        except Exception as e:
            self.logger.error("Failed to validate JWT token", error=str(e))
            return None
    
    async def check_permission(
        self,
        user_permissions: List[str],
        required_permission: Permission
    ) -> bool:
        """
        Check if user has required permission.
        
        Args:
            user_permissions: List of user permissions
            required_permission: Required permission
            
        Returns:
            True if user has permission, False otherwise
        """
        return required_permission.value in user_permissions
    
    async def check_role_permission(
        self,
        user_role: UserRole,
        required_permission: Permission
    ) -> bool:
        """
        Check if role has required permission.
        
        Args:
            user_role: User role
            required_permission: Required permission
            
        Returns:
            True if role has permission, False otherwise
        """
        role_permissions = self.role_permissions.get(user_role, [])
        return required_permission in role_permissions
    
    async def create_session(
        self,
        tenant_id: uuid.UUID,
        user_id: str,
        session_data: Dict[str, Any],
        user_agent: Optional[str] = None,
        expires_in_hours: int = 24
    ) -> str:
        """
        Create a new user session.
        
        Args:
            tenant_id: Tenant UUID
            user_id: User identifier
            session_data: Session data to store
            user_agent: User agent string
            expires_in_hours: Session expiration in hours
            
        Returns:
            Session ID
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Encrypt session data
                encrypted_data = self.security_utils.encrypt_sensitive_data(
                    str(session_data)
                )
                
                # Create session
                user_session = UserSession(
                    tenant_id=tenant_id,
                    user_id=self.security_utils.hash_phone_number(user_id),
                    session_data={"encrypted": encrypted_data},
                    user_agent=self._sanitize_user_agent(user_agent),
                    expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
                )
                
                session.add(user_session)
                await session.commit()
                
                # Log session creation
                await self.privacy_service.log_audit_event(
                    tenant_id=tenant_id,
                    event_type=AuditEventType.USER_LOGIN,
                    action="session_created",
                    user_id=user_id,
                    event_data={
                        "session_id": str(user_session.session_id),
                        "expires_at": user_session.expires_at.isoformat()
                    },
                    success=True
                )
                
                return str(user_session.session_id)
                
        except Exception as e:
            self.logger.error(
                "Failed to create session",
                tenant_id=str(tenant_id),
                user_id=user_id,
                error=str(e)
            )
            raise
    
    async def validate_session(
        self,
        tenant_id: uuid.UUID,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a user session.
        
        Args:
            tenant_id: Tenant UUID
            session_id: Session ID to validate
            
        Returns:
            Dict with session data if valid, None if invalid
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Find session
                from sqlalchemy import select
                result = await session.execute(
                    select(UserSession).where(
                        UserSession.tenant_id == tenant_id,
                        UserSession.session_id == uuid.UUID(session_id),
                        UserSession.is_active == True
                    )
                )
                user_session = result.scalar_one_or_none()
                
                if not user_session or user_session.is_expired:
                    return None
                
                # Update last activity
                user_session.last_activity_at = datetime.utcnow()
                await session.commit()
                
                # Decrypt session data
                encrypted_data = user_session.session_data.get("encrypted")
                if encrypted_data:
                    decrypted_data = self.security_utils.decrypt_sensitive_data(encrypted_data)
                    import json
                    session_data = json.loads(decrypted_data)
                else:
                    session_data = {}
                
                return {
                    "session_id": str(user_session.session_id),
                    "user_id": user_session.user_id,  # This is hashed
                    "session_data": session_data,
                    "expires_at": user_session.expires_at.isoformat(),
                    "last_activity_at": user_session.last_activity_at.isoformat()
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to validate session",
                tenant_id=str(tenant_id),
                session_id=session_id,
                error=str(e)
            )
            return None
    
    async def revoke_api_key(
        self,
        tenant_id: uuid.UUID,
        key_id: str,
        revoked_by: Optional[str] = None
    ) -> bool:
        """
        Revoke an API key.
        
        Args:
            tenant_id: Tenant UUID
            key_id: API key ID to revoke
            revoked_by: User revoking the key
            
        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Find and deactivate key
                from sqlalchemy import select, update
                result = await session.execute(
                    update(ApiKey)
                    .where(
                        ApiKey.tenant_id == tenant_id,
                        ApiKey.key_id == uuid.UUID(key_id)
                    )
                    .values(is_active=False)
                )
                
                if result.rowcount == 0:
                    return False
                
                await session.commit()
                
                # Log key revocation
                await self.privacy_service.log_audit_event(
                    tenant_id=tenant_id,
                    event_type=AuditEventType.SYSTEM_CONFIGURATION,
                    action="api_key_revoked",
                    user_id=revoked_by,
                    resource=f"api_key:{key_id}",
                    event_data={"revoked_by": revoked_by},
                    success=True
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to revoke API key",
                tenant_id=str(tenant_id),
                key_id=key_id,
                error=str(e)
            )
            return False
    
    async def invalidate_session(
        self,
        tenant_id: uuid.UUID,
        session_id: str,
        invalidated_by: Optional[str] = None
    ) -> bool:
        """
        Invalidate a user session.
        
        Args:
            tenant_id: Tenant UUID
            session_id: Session ID to invalidate
            invalidated_by: User invalidating the session
            
        Returns:
            True if invalidated successfully, False otherwise
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Find and deactivate session
                from sqlalchemy import select, update
                result = await session.execute(
                    update(UserSession)
                    .where(
                        UserSession.tenant_id == tenant_id,
                        UserSession.session_id == uuid.UUID(session_id)
                    )
                    .values(is_active=False)
                )
                
                if result.rowcount == 0:
                    return False
                
                await session.commit()
                
                # Log session invalidation
                await self.privacy_service.log_audit_event(
                    tenant_id=tenant_id,
                    event_type=AuditEventType.USER_LOGOUT,
                    action="session_invalidated",
                    user_id=invalidated_by,
                    event_data={
                        "session_id": session_id,
                        "invalidated_by": invalidated_by
                    },
                    success=True
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to invalidate session",
                tenant_id=str(tenant_id),
                session_id=session_id,
                error=str(e)
            )
            return False
    
    def _sanitize_user_agent(self, user_agent: Optional[str]) -> Optional[str]:
        """Sanitize user agent string for privacy compliance."""
        if not user_agent:
            return None
        
        import re
        # Remove version numbers and specific identifiers
        sanitized = re.sub(r'\d+\.\d+[\.\d]*', 'X.X', user_agent)
        sanitized = re.sub(r'\([^)]*\)', '(sanitized)', sanitized)
        
        return sanitized[:200]  # Limit length


# Singleton instance
auth_service = AuthService()