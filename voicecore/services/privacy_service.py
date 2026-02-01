"""
Privacy compliance service for VoiceCore AI.

Implements privacy-compliant audit logging, data encryption,
and ensures no IP/geolocation data storage per Requirements 5.1, 5.3, 5.5.
"""

import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

from voicecore.database import get_db_session, set_tenant_context
from voicecore.utils.security import SecurityUtils, sanitize_log_data
from voicecore.logging import get_logger
from voicecore.models.base import BaseModel, TimestampMixin, TenantMixin


logger = get_logger(__name__)


class AuditEventType(Enum):
    """Types of audit events for privacy compliance."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    CALL_INITIATED = "call_initiated"
    CALL_COMPLETED = "call_completed"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CONFIGURATION = "system_configuration"
    SECURITY_EVENT = "security_event"
    PRIVACY_VIOLATION = "privacy_violation"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"


class AuditLog(BaseModel, TimestampMixin, TenantMixin):
    """
    Privacy-compliant audit log model.
    
    CRITICAL: This model ensures no IP addresses, geolocation,
    or location data is stored per Requirements 5.1 and 5.5.
    """
    
    # Event identification
    event_id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        nullable=False,
        unique=True,
        doc="Unique event identifier"
    )
    
    event_type = Column(
        String(50),
        nullable=False,
        doc="Type of audit event"
    )
    
    # User and session information (privacy-compliant)
    user_id = Column(
        String(255),
        nullable=True,
        doc="User identifier (hashed for privacy)"
    )
    
    session_id = Column(
        String(255),
        nullable=True,
        doc="Session identifier (hashed for privacy)"
    )
    
    correlation_id = Column(
        String(255),
        nullable=True,
        doc="Request correlation ID for tracking"
    )
    
    # Event details (sanitized)
    action = Column(
        String(255),
        nullable=False,
        doc="Action performed"
    )
    
    resource = Column(
        String(255),
        nullable=True,
        doc="Resource accessed or modified"
    )
    
    # Sanitized event data
    event_data = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Sanitized event data (no sensitive information)"
    )
    
    # Result and status
    success = Column(
        Boolean,
        nullable=False,
        doc="Whether the action was successful"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if action failed (sanitized)"
    )
    
    # Security metadata
    user_agent = Column(
        String(500),
        nullable=True,
        doc="User agent string (sanitized)"
    )
    
    # CRITICAL: NO IP ADDRESS OR LOCATION DATA STORED
    # This ensures compliance with Requirements 5.1 and 5.5
    
    def __repr__(self) -> str:
        return f"<AuditLog(event_id={self.event_id}, event_type='{self.event_type}')>"


class PrivacyService:
    """
    Privacy compliance service implementing Requirements 5.1, 5.3, 5.5.
    
    Ensures:
    - No IP addresses or geolocation data storage
    - Privacy-compliant audit logging
    - Data encryption for all sensitive operations
    """
    
    def __init__(self):
        self.logger = logger
        self.security_utils = SecurityUtils()
    
    async def log_audit_event(
        self,
        tenant_id: uuid.UUID,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        resource: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Log audit event with privacy compliance.
        
        CRITICAL: This method ensures no IP addresses, geolocation,
        or location data is logged per Requirements 5.1 and 5.5.
        
        Args:
            tenant_id: Tenant UUID
            event_type: Type of audit event
            action: Action performed
            user_id: User identifier (will be hashed)
            session_id: Session identifier (will be hashed)
            correlation_id: Request correlation ID
            resource: Resource accessed or modified
            event_data: Event data (will be sanitized)
            success: Whether action was successful
            error_message: Error message if failed
            user_agent: User agent string (will be sanitized)
            
        Returns:
            bool: True if audit log was created successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Sanitize all input data to ensure privacy compliance
                sanitized_event_data = sanitize_log_data(event_data or {})
                sanitized_error_message = self.security_utils.sanitize_data(error_message) if error_message else None
                sanitized_user_agent = self._sanitize_user_agent(user_agent) if user_agent else None
                
                # Hash user identifiers for privacy
                hashed_user_id = self.security_utils.hash_phone_number(user_id) if user_id else None
                hashed_session_id = self.security_utils.hash_phone_number(session_id) if session_id else None
                
                # Create audit log entry
                audit_log = AuditLog(
                    tenant_id=tenant_id,
                    event_id=uuid.uuid4(),
                    event_type=event_type.value,
                    user_id=hashed_user_id,
                    session_id=hashed_session_id,
                    correlation_id=correlation_id or self.security_utils.generate_correlation_id(),
                    action=action,
                    resource=resource,
                    event_data=sanitized_event_data,
                    success=success,
                    error_message=sanitized_error_message,
                    user_agent=sanitized_user_agent
                )
                
                session.add(audit_log)
                await session.commit()
                
                self.logger.info(
                    "Audit event logged",
                    tenant_id=str(tenant_id),
                    event_type=event_type.value,
                    action=action,
                    success=success
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to log audit event",
                tenant_id=str(tenant_id),
                event_type=event_type.value,
                error=str(e)
            )
            return False
    
    async def encrypt_call_data(
        self,
        tenant_id: uuid.UUID,
        call_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Encrypt sensitive call data per Requirement 5.3.
        
        Args:
            tenant_id: Tenant UUID
            call_data: Call data to encrypt
            
        Returns:
            Dict with encrypted sensitive fields
        """
        try:
            encrypted_data = call_data.copy()
            
            # Fields that need encryption
            sensitive_fields = [
                'caller_phone_number',
                'transcript',
                'recording_url',
                'notes',
                'customer_data'
            ]
            
            for field in sensitive_fields:
                if field in encrypted_data and encrypted_data[field]:
                    # Encrypt the sensitive data
                    encrypted_value = self.security_utils.encrypt_sensitive_data(
                        str(encrypted_data[field])
                    )
                    encrypted_data[field] = encrypted_value
                    
                    # Log encryption event
                    await self.log_audit_event(
                        tenant_id=tenant_id,
                        event_type=AuditEventType.DATA_MODIFICATION,
                        action="encrypt_call_data",
                        resource=f"call_data.{field}",
                        event_data={"field": field, "encrypted": True},
                        success=True
                    )
            
            return encrypted_data
            
        except Exception as e:
            self.logger.error(
                "Failed to encrypt call data",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            
            # Log encryption failure
            await self.log_audit_event(
                tenant_id=tenant_id,
                event_type=AuditEventType.SECURITY_EVENT,
                action="encrypt_call_data_failed",
                event_data={"error": str(e)},
                success=False,
                error_message=str(e)
            )
            
            raise
    
    async def decrypt_call_data(
        self,
        tenant_id: uuid.UUID,
        encrypted_call_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Decrypt sensitive call data per Requirement 5.3.
        
        Args:
            tenant_id: Tenant UUID
            encrypted_call_data: Encrypted call data
            
        Returns:
            Dict with decrypted sensitive fields
        """
        try:
            decrypted_data = encrypted_call_data.copy()
            
            # Fields that need decryption
            sensitive_fields = [
                'caller_phone_number',
                'transcript',
                'recording_url',
                'notes',
                'customer_data'
            ]
            
            for field in sensitive_fields:
                if field in decrypted_data and decrypted_data[field]:
                    try:
                        # Decrypt the sensitive data
                        decrypted_value = self.security_utils.decrypt_sensitive_data(
                            decrypted_data[field]
                        )
                        decrypted_data[field] = decrypted_value
                        
                        # Log decryption event
                        await self.log_audit_event(
                            tenant_id=tenant_id,
                            event_type=AuditEventType.DATA_ACCESS,
                            action="decrypt_call_data",
                            resource=f"call_data.{field}",
                            event_data={"field": field, "decrypted": True},
                            success=True
                        )
                        
                    except Exception as decrypt_error:
                        # If decryption fails, the data might not be encrypted
                        self.logger.warning(
                            "Failed to decrypt field, assuming unencrypted",
                            field=field,
                            error=str(decrypt_error)
                        )
            
            return decrypted_data
            
        except Exception as e:
            self.logger.error(
                "Failed to decrypt call data",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            
            # Log decryption failure
            await self.log_audit_event(
                tenant_id=tenant_id,
                event_type=AuditEventType.SECURITY_EVENT,
                action="decrypt_call_data_failed",
                event_data={"error": str(e)},
                success=False,
                error_message=str(e)
            )
            
            raise
    
    async def validate_privacy_compliance(
        self,
        tenant_id: uuid.UUID,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that data complies with privacy requirements.
        
        Ensures no IP addresses, geolocation, or location data
        is present per Requirements 5.1 and 5.5.
        
        Args:
            tenant_id: Tenant UUID
            data: Data to validate
            
        Returns:
            Dict with validation results and sanitized data
        """
        try:
            validation_result = {
                "compliant": True,
                "violations": [],
                "sanitized_data": None,
                "warnings": []
            }
            
            # Check for privacy violations
            violations = self._detect_privacy_violations(data)
            
            if violations:
                validation_result["compliant"] = False
                validation_result["violations"] = violations
                
                # Log privacy violation
                await self.log_audit_event(
                    tenant_id=tenant_id,
                    event_type=AuditEventType.PRIVACY_VIOLATION,
                    action="privacy_validation_failed",
                    event_data={
                        "violations": violations,
                        "data_keys": list(data.keys()) if isinstance(data, dict) else []
                    },
                    success=False,
                    error_message=f"Privacy violations detected: {', '.join(violations)}"
                )
            
            # Sanitize data regardless of violations
            sanitized_data = self.security_utils.sanitize_data(data)
            validation_result["sanitized_data"] = sanitized_data
            
            # Log validation event
            await self.log_audit_event(
                tenant_id=tenant_id,
                event_type=AuditEventType.DATA_ACCESS,
                action="privacy_validation",
                event_data={
                    "compliant": validation_result["compliant"],
                    "violation_count": len(violations)
                },
                success=validation_result["compliant"]
            )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(
                "Failed to validate privacy compliance",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            
            return {
                "compliant": False,
                "violations": ["validation_error"],
                "sanitized_data": self.security_utils.sanitize_data(data),
                "warnings": [f"Validation error: {str(e)}"]
            }
    
    async def get_audit_logs(
        self,
        tenant_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with privacy compliance.
        
        Args:
            tenant_id: Tenant UUID
            start_date: Start date for log retrieval
            end_date: End date for log retrieval
            event_type: Filter by event type
            user_id: Filter by user ID (will be hashed)
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log entries
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Build query
                from sqlalchemy import select, and_
                
                query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
                
                if start_date:
                    query = query.where(AuditLog.created_at >= start_date)
                
                if end_date:
                    query = query.where(AuditLog.created_at <= end_date)
                
                if event_type:
                    query = query.where(AuditLog.event_type == event_type.value)
                
                if user_id:
                    hashed_user_id = self.security_utils.hash_phone_number(user_id)
                    query = query.where(AuditLog.user_id == hashed_user_id)
                
                query = query.order_by(AuditLog.created_at.desc()).limit(limit)
                
                result = await session.execute(query)
                audit_logs = result.scalars().all()
                
                # Convert to dict format
                logs_data = []
                for log in audit_logs:
                    logs_data.append({
                        "event_id": str(log.event_id),
                        "event_type": log.event_type,
                        "action": log.action,
                        "resource": log.resource,
                        "success": log.success,
                        "created_at": log.created_at.isoformat(),
                        "event_data": log.event_data,
                        "correlation_id": log.correlation_id
                        # Note: user_id and session_id are hashed and not returned
                    })
                
                # Log audit access
                await self.log_audit_event(
                    tenant_id=tenant_id,
                    event_type=AuditEventType.DATA_ACCESS,
                    action="get_audit_logs",
                    event_data={
                        "log_count": len(logs_data),
                        "filters": {
                            "start_date": start_date.isoformat() if start_date else None,
                            "end_date": end_date.isoformat() if end_date else None,
                            "event_type": event_type.value if event_type else None
                        }
                    },
                    success=True
                )
                
                return logs_data
                
        except Exception as e:
            self.logger.error(
                "Failed to retrieve audit logs",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return []
    
    def _detect_privacy_violations(self, data: Any) -> List[str]:
        """
        Detect privacy violations in data.
        
        Returns list of violation types found.
        """
        violations = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                key_lower = key.lower()
                
                # Check for location-related keys
                if any(keyword in key_lower for keyword in self.security_utils.LOCATION_KEYWORDS):
                    violations.append(f"location_data_in_key: {key}")
                
                # Check for IP address keys
                if 'ip' in key_lower or 'addr' in key_lower:
                    violations.append(f"ip_address_in_key: {key}")
                
                # Recursively check values
                violations.extend(self._detect_privacy_violations(value))
        
        elif isinstance(data, list):
            for item in data:
                violations.extend(self._detect_privacy_violations(item))
        
        elif isinstance(data, str):
            # Check for sensitive patterns in string data
            for pattern_name, pattern in self.security_utils.SENSITIVE_PATTERNS.items():
                if pattern_name in ['ip_address', 'ipv6_address', 'coordinates']:
                    import re
                    if re.search(pattern, data):
                        violations.append(f"sensitive_pattern: {pattern_name}")
        
        return violations
    
    def _sanitize_user_agent(self, user_agent: str) -> str:
        """
        Sanitize user agent string to remove potentially sensitive information.
        """
        if not user_agent:
            return user_agent
        
        # Remove version numbers and specific identifiers
        import re
        
        # Keep only basic browser/OS information
        sanitized = re.sub(r'\d+\.\d+[\.\d]*', 'X.X', user_agent)
        sanitized = re.sub(r'\([^)]*\)', '(sanitized)', sanitized)
        
        return sanitized[:200]  # Limit length


# Convenience functions for common privacy operations
async def log_user_action(
    tenant_id: uuid.UUID,
    action: str,
    user_id: Optional[str] = None,
    resource: Optional[str] = None,
    success: bool = True,
    **kwargs
) -> bool:
    """Log user action with privacy compliance."""
    privacy_service = PrivacyService()
    return await privacy_service.log_audit_event(
        tenant_id=tenant_id,
        event_type=AuditEventType.DATA_ACCESS,
        action=action,
        user_id=user_id,
        resource=resource,
        success=success,
        **kwargs
    )


async def encrypt_sensitive_call_data(
    tenant_id: uuid.UUID,
    call_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Encrypt sensitive call data."""
    privacy_service = PrivacyService()
    return await privacy_service.encrypt_call_data(tenant_id, call_data)


async def validate_data_privacy(
    tenant_id: uuid.UUID,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate data for privacy compliance."""
    privacy_service = PrivacyService()
    return await privacy_service.validate_privacy_compliance(tenant_id, data)