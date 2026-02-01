"""
API security middleware for VoiceCore AI.

Implements comprehensive API security including authentication,
rate limiting, and webhook validation per Requirements 10.5 and 10.2.
"""

import uuid
import time
import hmac
import hashlib
from typing import Callable, Dict, Any, Optional, List
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from voicecore.services.auth_service import AuthService, Permission
from voicecore.services.intrusion_detection_service import intrusion_detection_service
from voicecore.services.privacy_service import PrivacyService, AuditEventType
from voicecore.utils.security import SecurityUtils
from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, window: int, retry_after: int):
        super().__init__(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} requests per {window} seconds"
        )
        self.limit = limit
        self.window = window
        self.retry_after = retry_after


class ApiSecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive API security middleware.
    
    Implements authentication, authorization, rate limiting,
    and security monitoring per Requirements 10.5 and 10.2.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.auth_service = AuthService()
        self.privacy_service = PrivacyService()
        self.security_utils = SecurityUtils()
        
        # Rate limiting storage (in production, use Redis)
        self.rate_limit_storage = defaultdict(lambda: deque())
        
        # Protected endpoints and their required permissions
        self.protected_endpoints = {
            # Call management
            "/api/calls": {
                "GET": Permission.CALL_VIEW,
                "POST": Permission.CALL_CREATE,
                "PUT": Permission.CALL_UPDATE,
                "DELETE": Permission.CALL_DELETE
            },
            "/api/calls/{call_id}": {
                "GET": Permission.CALL_VIEW,
                "PUT": Permission.CALL_UPDATE,
                "DELETE": Permission.CALL_DELETE
            },
            
            # Agent management
            "/api/agents": {
                "GET": Permission.AGENT_VIEW,
                "POST": Permission.AGENT_CREATE,
                "PUT": Permission.AGENT_UPDATE,
                "DELETE": Permission.AGENT_DELETE
            },
            "/api/agents/{agent_id}": {
                "GET": Permission.AGENT_VIEW,
                "PUT": Permission.AGENT_UPDATE,
                "DELETE": Permission.AGENT_DELETE
            },
            
            # Analytics
            "/api/analytics": {
                "GET": Permission.ANALYTICS_VIEW
            },
            "/api/analytics/export": {
                "GET": Permission.ANALYTICS_EXPORT,
                "POST": Permission.ANALYTICS_EXPORT
            },
            
            # Administration
            "/api/admin": {
                "GET": Permission.ADMIN_SYSTEM,
                "POST": Permission.ADMIN_SYSTEM,
                "PUT": Permission.ADMIN_SYSTEM,
                "DELETE": Permission.ADMIN_SYSTEM
            },
            "/api/tenant": {
                "GET": Permission.ADMIN_TENANT,
                "POST": Permission.ADMIN_TENANT,
                "PUT": Permission.ADMIN_TENANT,
                "DELETE": Permission.ADMIN_TENANT
            }
        }
        
        # Rate limits by endpoint category
        self.rate_limits = {
            "default": {"requests": 100, "window": 60},  # 100 req/min
            "auth": {"requests": 10, "window": 60},      # 10 req/min
            "admin": {"requests": 50, "window": 60},     # 50 req/min
            "api": {"requests": 200, "window": 60},      # 200 req/min
            "webhook": {"requests": 1000, "window": 60}  # 1000 req/min
        }
        
        # Public endpoints that don't require authentication
        self.public_endpoints = [
            "/health",
            "/docs",
            "/openapi.json",
            "/api/webhooks/twilio",  # Webhook endpoints
            "/api/webhooks/openai"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive security checks."""
        start_time = time.time()
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        
        try:
            # 1. Check if endpoint is public
            if self._is_public_endpoint(request.url.path):
                # Still apply basic rate limiting to public endpoints
                await self._apply_rate_limiting(request, "default")
                return await call_next(request)
            
            # 2. Intrusion detection
            intrusion_result = await self._check_intrusion_detection(request)
            if intrusion_result["blocked"]:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Request blocked by security system",
                        "correlation_id": correlation_id
                    }
                )
            
            # 3. Authentication
            auth_result = await self._authenticate_request(request)
            if not auth_result["authenticated"]:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Authentication required",
                        "correlation_id": correlation_id
                    }
                )
            
            # Store auth info in request state
            request.state.auth_info = auth_result
            request.state.tenant_id = uuid.UUID(auth_result["tenant_id"])
            
            # 4. Authorization
            if not await self._authorize_request(request, auth_result):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Insufficient permissions",
                        "correlation_id": correlation_id
                    }
                )
            
            # 5. Rate limiting (with user-specific limits)
            rate_limit_category = self._get_rate_limit_category(request.url.path)
            await self._apply_rate_limiting(
                request, 
                rate_limit_category, 
                auth_result.get("rate_limit_per_minute")
            )
            
            # 6. Webhook validation (if applicable)
            if request.url.path.startswith("/api/webhooks/"):
                if not await self._validate_webhook(request):
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Invalid webhook signature",
                            "correlation_id": correlation_id
                        }
                    )
            
            # Process request
            response = await call_next(request)
            
            # 7. Log successful request
            await self._log_api_request(
                request=request,
                response=response,
                auth_info=auth_result,
                processing_time=time.time() - start_time,
                correlation_id=correlation_id
            )
            
            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except RateLimitExceeded as e:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "limit": e.limit,
                    "retry_after": e.retry_after,
                    "correlation_id": correlation_id
                },
                headers={"Retry-After": str(e.retry_after)}
            )
            
        except Exception as e:
            logger.error(
                "API security middleware error",
                correlation_id=correlation_id,
                error=str(e),
                path=request.url.path
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "correlation_id": correlation_id
                }
            )
    
    async def _check_intrusion_detection(self, request: Request) -> Dict[str, Any]:
        """Check request against intrusion detection system."""
        try:
            # Prepare request data for analysis
            request_data = {
                "method": request.method,
                "path": request.url.path,
                "headers": dict(request.headers),
                "query_params": dict(request.query_params)
            }
            
            # Add body for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if body:
                        request._body = body  # Cache for later use
                        if request.headers.get("content-type", "").startswith("application/json"):
                            import json
                            try:
                                request_data["body"] = json.loads(body.decode())
                            except json.JSONDecodeError:
                                request_data["body"] = {"raw": body.decode()[:1000]}
                except Exception:
                    pass  # Skip body analysis if it fails
            
            # Use a default tenant ID for intrusion detection
            # In a real implementation, this might be extracted from the request
            default_tenant_id = uuid.uuid4()
            
            # Analyze request
            analysis_result = await intrusion_detection_service.analyze_request(
                tenant_id=default_tenant_id,
                request_data=request_data,
                correlation_id=getattr(request.state, 'correlation_id', None)
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error("Failed to check intrusion detection", error=str(e))
            return {"blocked": False, "threat_detected": False}
    
    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """Authenticate the request using API key or JWT token."""
        try:
            # Check for API key in header
            api_key = request.headers.get("X-API-Key")
            if api_key:
                return await self._authenticate_api_key(request, api_key)
            
            # Check for JWT token in Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix
                return await self._authenticate_jwt_token(request, token)
            
            # Check for session-based authentication
            session_id = request.headers.get("X-Session-ID")
            if session_id:
                return await self._authenticate_session(request, session_id)
            
            return {"authenticated": False, "reason": "no_credentials"}
            
        except Exception as e:
            logger.error("Failed to authenticate request", error=str(e))
            return {"authenticated": False, "reason": "auth_error"}
    
    async def _authenticate_api_key(self, request: Request, api_key: str) -> Dict[str, Any]:
        """Authenticate using API key."""
        try:
            # Extract tenant ID from request (could be in path, header, or query)
            tenant_id = self._extract_tenant_id(request)
            if not tenant_id:
                return {"authenticated": False, "reason": "no_tenant_id"}
            
            # Validate API key
            key_info = await self.auth_service.validate_api_key(
                tenant_id=uuid.UUID(tenant_id),
                api_key=api_key
            )
            
            if not key_info:
                return {"authenticated": False, "reason": "invalid_api_key"}
            
            return {
                "authenticated": True,
                "auth_type": "api_key",
                "tenant_id": tenant_id,
                "key_id": key_info["key_id"],
                "permissions": key_info["permissions"],
                "scopes": key_info["scopes"],
                "rate_limit_per_minute": key_info["rate_limit_per_minute"]
            }
            
        except Exception as e:
            logger.error("Failed to authenticate API key", error=str(e))
            return {"authenticated": False, "reason": "api_key_error"}
    
    async def _authenticate_jwt_token(self, request: Request, token: str) -> Dict[str, Any]:
        """Authenticate using JWT token."""
        try:
            # Validate JWT token
            token_info = await self.auth_service.validate_jwt_token(token)
            
            if not token_info:
                return {"authenticated": False, "reason": "invalid_jwt_token"}
            
            return {
                "authenticated": True,
                "auth_type": "jwt_token",
                "tenant_id": token_info["tenant_id"],
                "user_id": token_info["user_id"],
                "role": token_info["role"],
                "permissions": token_info["permissions"],
                "jwt_id": token_info["jwt_id"]
            }
            
        except Exception as e:
            logger.error("Failed to authenticate JWT token", error=str(e))
            return {"authenticated": False, "reason": "jwt_token_error"}
    
    async def _authenticate_session(self, request: Request, session_id: str) -> Dict[str, Any]:
        """Authenticate using session ID."""
        try:
            # Extract tenant ID
            tenant_id = self._extract_tenant_id(request)
            if not tenant_id:
                return {"authenticated": False, "reason": "no_tenant_id"}
            
            # Validate session
            session_info = await self.auth_service.validate_session(
                tenant_id=uuid.UUID(tenant_id),
                session_id=session_id
            )
            
            if not session_info:
                return {"authenticated": False, "reason": "invalid_session"}
            
            return {
                "authenticated": True,
                "auth_type": "session",
                "tenant_id": tenant_id,
                "session_id": session_info["session_id"],
                "user_id": session_info["user_id"],
                "session_data": session_info["session_data"]
            }
            
        except Exception as e:
            logger.error("Failed to authenticate session", error=str(e))
            return {"authenticated": False, "reason": "session_error"}
    
    async def _authorize_request(self, request: Request, auth_info: Dict[str, Any]) -> bool:
        """Authorize the request based on permissions."""
        try:
            # Get required permission for this endpoint
            required_permission = self._get_required_permission(
                request.url.path, 
                request.method
            )
            
            if not required_permission:
                # No specific permission required
                return True
            
            # Check permissions
            user_permissions = auth_info.get("permissions", [])
            
            # Check if user has the required permission
            return await self.auth_service.check_permission(
                user_permissions=user_permissions,
                required_permission=required_permission
            )
            
        except Exception as e:
            logger.error("Failed to authorize request", error=str(e))
            return False
    
    async def _apply_rate_limiting(
        self, 
        request: Request, 
        category: str, 
        custom_limit: Optional[int] = None
    ):
        """Apply rate limiting to the request."""
        try:
            # Get rate limit configuration
            rate_config = self.rate_limits.get(category, self.rate_limits["default"])
            
            # Use custom limit if provided (from API key)
            if custom_limit:
                rate_config = {"requests": custom_limit, "window": 60}
            
            # Generate rate limit key (use auth info if available)
            auth_info = getattr(request.state, 'auth_info', {})
            if auth_info.get("authenticated"):
                if auth_info.get("key_id"):
                    rate_key = f"api_key:{auth_info['key_id']}"
                elif auth_info.get("user_id"):
                    rate_key = f"user:{auth_info['user_id']}"
                else:
                    rate_key = f"tenant:{auth_info['tenant_id']}"
            else:
                # Use a generic key for unauthenticated requests
                rate_key = f"ip:anonymous"
            
            # Check rate limit
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(seconds=rate_config["window"])
            
            # Clean old entries
            while (self.rate_limit_storage[rate_key] and 
                   self.rate_limit_storage[rate_key][0] < window_start):
                self.rate_limit_storage[rate_key].popleft()
            
            # Check current count
            current_count = len(self.rate_limit_storage[rate_key])
            
            if current_count >= rate_config["requests"]:
                # Calculate retry after
                oldest_request = self.rate_limit_storage[rate_key][0]
                retry_after = int((oldest_request + timedelta(seconds=rate_config["window"]) - current_time).total_seconds())
                
                raise RateLimitExceeded(
                    limit=rate_config["requests"],
                    window=rate_config["window"],
                    retry_after=max(1, retry_after)
                )
            
            # Add current request
            self.rate_limit_storage[rate_key].append(current_time)
            
        except RateLimitExceeded:
            raise  # Re-raise rate limit exceptions
        except Exception as e:
            logger.error("Failed to apply rate limiting", error=str(e))
            # Don't block request on rate limiting errors
    
    async def _validate_webhook(self, request: Request) -> bool:
        """Validate webhook signature."""
        try:
            # Get webhook signature from headers
            signature = request.headers.get("X-Twilio-Signature") or request.headers.get("X-OpenAI-Signature")
            
            if not signature:
                return False
            
            # Get request body
            body = getattr(request, '_body', None)
            if body is None:
                body = await request.body()
                request._body = body
            
            # Validate signature based on webhook type
            if request.url.path.startswith("/api/webhooks/twilio"):
                return self._validate_twilio_webhook(signature, body, request.url)
            elif request.url.path.startswith("/api/webhooks/openai"):
                return self._validate_openai_webhook(signature, body)
            
            return False
            
        except Exception as e:
            logger.error("Failed to validate webhook", error=str(e))
            return False
    
    def _validate_twilio_webhook(self, signature: str, body: bytes, url) -> bool:
        """Validate Twilio webhook signature."""
        try:
            # Get Twilio auth token from settings
            auth_token = settings.TWILIO_AUTH_TOKEN
            if not auth_token:
                return False
            
            # Create expected signature
            url_str = str(url)
            expected_signature = hmac.new(
                auth_token.encode(),
                (url_str + body.decode()).encode(),
                hashlib.sha1
            ).digest()
            
            import base64
            expected_signature_b64 = base64.b64encode(expected_signature).decode()
            
            return hmac.compare_digest(signature, expected_signature_b64)
            
        except Exception as e:
            logger.error("Failed to validate Twilio webhook", error=str(e))
            return False
    
    def _validate_openai_webhook(self, signature: str, body: bytes) -> bool:
        """Validate OpenAI webhook signature."""
        try:
            # Get OpenAI webhook secret from settings
            webhook_secret = settings.OPENAI_WEBHOOK_SECRET
            if not webhook_secret:
                return False
            
            # Create expected signature
            expected_signature = hmac.new(
                webhook_secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, f"sha256={expected_signature}")
            
        except Exception as e:
            logger.error("Failed to validate OpenAI webhook", error=str(e))
            return False
    
    async def _log_api_request(
        self,
        request: Request,
        response: Response,
        auth_info: Dict[str, Any],
        processing_time: float,
        correlation_id: str
    ):
        """Log API request for audit trail."""
        try:
            tenant_id = auth_info.get("tenant_id")
            if not tenant_id:
                return
            
            # Prepare event data
            event_data = {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "processing_time_ms": round(processing_time * 1000, 2),
                "auth_type": auth_info.get("auth_type"),
                "user_agent": request.headers.get("user-agent", "")[:100]
            }
            
            # Determine event type
            if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
                event_type = AuditEventType.DATA_MODIFICATION
            else:
                event_type = AuditEventType.DATA_ACCESS
            
            # Log audit event
            await self.privacy_service.log_audit_event(
                tenant_id=uuid.UUID(tenant_id),
                event_type=event_type,
                action=f"api_{request.method.lower()}",
                user_id=auth_info.get("user_id"),
                correlation_id=correlation_id,
                resource=request.url.path,
                event_data=event_data,
                success=200 <= response.status_code < 400
            )
            
        except Exception as e:
            logger.error("Failed to log API request", error=str(e))
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (doesn't require authentication)."""
        return any(public_path in path for public_path in self.public_endpoints)
    
    def _get_required_permission(self, path: str, method: str) -> Optional[Permission]:
        """Get required permission for endpoint and method."""
        # Check exact path match first
        if path in self.protected_endpoints:
            return self.protected_endpoints[path].get(method)
        
        # Check pattern matches (simplified)
        for pattern, permissions in self.protected_endpoints.items():
            if "{" in pattern:  # Path parameter pattern
                pattern_parts = pattern.split("/")
                path_parts = path.split("/")
                
                if len(pattern_parts) == len(path_parts):
                    match = True
                    for i, (pattern_part, path_part) in enumerate(zip(pattern_parts, path_parts)):
                        if not (pattern_part == path_part or pattern_part.startswith("{")):
                            match = False
                            break
                    
                    if match:
                        return permissions.get(method)
        
        return None
    
    def _get_rate_limit_category(self, path: str) -> str:
        """Get rate limit category for endpoint."""
        if "/auth" in path:
            return "auth"
        elif "/admin" in path:
            return "admin"
        elif "/api/webhooks" in path:
            return "webhook"
        elif "/api" in path:
            return "api"
        else:
            return "default"
    
    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request."""
        # Try path parameters
        if hasattr(request, 'path_params') and 'tenant_id' in request.path_params:
            return request.path_params['tenant_id']
        
        # Try query parameters
        if 'tenant_id' in request.query_params:
            return request.query_params['tenant_id']
        
        # Try headers
        if 'X-Tenant-ID' in request.headers:
            return request.headers['X-Tenant-ID']
        
        return None


# Utility function to add middleware to FastAPI app
def add_api_security_middleware(app):
    """Add API security middleware to FastAPI app."""
    app.add_middleware(ApiSecurityMiddleware)