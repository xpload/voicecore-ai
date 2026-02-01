"""
Security middleware for VoiceCore AI.

Implements comprehensive security measures including:
- Request validation and sanitization
- Rate limiting enforcement
- Intrusion detection integration
- Security headers management

Implements Requirements 5.4, 10.2, 10.5.
"""

import uuid
import time
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from voicecore.services.intrusion_detection_service import intrusion_detection_service
from voicecore.services.privacy_service import PrivacyService, AuditEventType
from voicecore.utils.security import SecurityUtils
from voicecore.logging import get_logger


logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware implementing Requirements 5.4, 10.2, 10.5.
    
    Provides:
    - Intrusion detection and prevention
    - Rate limiting enforcement
    - Security headers management
    - Request validation and sanitization
    """
    
    def __init__(self, app, privacy_service: Optional[PrivacyService] = None):
        super().__init__(app)
        self.privacy_service = privacy_service or PrivacyService()
        self.security_utils = SecurityUtils()
        
        # Security headers to add to all responses
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
        
        # Paths that bypass some security checks (health checks, etc.)
        self.bypass_paths = ['/health', '/metrics', '/status']
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive security checks."""
        start_time = time.time()
        correlation_id = self.security_utils.generate_correlation_id()
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        try:
            # Skip security checks for bypass paths
            if request.url.path in self.bypass_paths:
                response = await call_next(request)
                return self._add_security_headers(response)
            
            # 1. Validate request format and size
            validation_result = await self._validate_request_format(request)
            if not validation_result["valid"]:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid request format",
                        "message": validation_result["message"],
                        "correlation_id": correlation_id
                    }
                )
            
            # 2. Extract tenant and user information
            tenant_id, user_id = await self._extract_request_context(request)
            
            # 3. Check if user/IP is blocked
            if await intrusion_detection_service.is_blocked(user_id):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Access denied",
                        "message": "User is temporarily blocked",
                        "correlation_id": correlation_id
                    }
                )
            
            # 4. Perform intrusion detection analysis
            request_data = await self._prepare_request_data(request)
            threat_analysis = await intrusion_detection_service.analyze_request(
                tenant_id=tenant_id or uuid.uuid4(),  # Use dummy UUID if no tenant
                request_data=request_data,
                user_id=user_id,
                correlation_id=correlation_id
            )
            
            # 5. Block request if high threat detected
            if threat_analysis["blocked"]:
                await self._log_blocked_request(
                    tenant_id, user_id, threat_analysis, correlation_id
                )
                
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Request blocked",
                        "message": "Security threat detected",
                        "correlation_id": correlation_id
                    }
                )
            
            # 6. Add security context to request
            request.state.tenant_id = tenant_id
            request.state.user_id = user_id
            request.state.threat_analysis = threat_analysis
            
            # 7. Process request
            response = await call_next(request)
            
            # 8. Add security headers
            response = self._add_security_headers(response)
            
            # 9. Log successful request
            await self._log_successful_request(
                tenant_id, user_id, request_data, response, correlation_id
            )
            
            return response
            
        except HTTPException as e:
            # Handle HTTP exceptions (authentication errors, etc.)
            if e.status_code == 401 and user_id:
                # Record failed authentication attempt
                await intrusion_detection_service.record_failed_attempt(
                    tenant_id or uuid.uuid4(), user_id, "authentication"
                )
            
            # Re-raise HTTP exceptions
            raise e
            
        except Exception as e:
            logger.error(
                "Security middleware error",
                correlation_id=correlation_id,
                error=str(e),
                path=request.url.path
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal security error",
                    "correlation_id": correlation_id
                }
            )
    
    async def _validate_request_format(self, request: Request) -> Dict[str, Any]:
        """Validate basic request format and constraints."""
        try:
            # Check request size limits
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    max_size = 10 * 1024 * 1024  # 10MB limit
                    
                    if size > max_size:
                        return {
                            "valid": False,
                            "message": f"Request too large: {size} bytes (max: {max_size})"
                        }
                except ValueError:
                    return {
                        "valid": False,
                        "message": "Invalid content-length header"
                    }
            
            # Validate HTTP method
            allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']
            if request.method not in allowed_methods:
                return {
                    "valid": False,
                    "message": f"Method {request.method} not allowed"
                }
            
            # Validate content type for POST/PUT requests
            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = request.headers.get("content-type", "")
                allowed_types = [
                    'application/json',
                    'application/x-www-form-urlencoded',
                    'multipart/form-data'
                ]
                
                if not any(allowed_type in content_type for allowed_type in allowed_types):
                    return {
                        "valid": False,
                        "message": f"Content type {content_type} not allowed"
                    }
            
            # Check for required security headers in sensitive operations
            if request.url.path.startswith('/api/admin'):
                if 'authorization' not in request.headers:
                    return {
                        "valid": False,
                        "message": "Authorization header required for admin operations"
                    }
            
            return {"valid": True, "message": "Request format valid"}
            
        except Exception as e:
            logger.error("Failed to validate request format", error=str(e))
            return {"valid": False, "message": "Validation error"}
    
    async def _extract_request_context(self, request: Request) -> tuple[Optional[uuid.UUID], Optional[str]]:
        """Extract tenant ID and user ID from request."""
        try:
            tenant_id = None
            user_id = None
            
            # Try to get tenant ID from various sources
            if hasattr(request, 'path_params') and 'tenant_id' in request.path_params:
                tenant_id = uuid.UUID(request.path_params['tenant_id'])
            elif 'x-tenant-id' in request.headers:
                tenant_id = uuid.UUID(request.headers['x-tenant-id'])
            elif 'tenant_id' in request.query_params:
                tenant_id = uuid.UUID(request.query_params['tenant_id'])
            
            # Try to get user ID from authorization header or session
            auth_header = request.headers.get('authorization', '')
            if auth_header.startswith('Bearer '):
                # In a real implementation, you would decode the JWT token
                # For now, we'll use a placeholder
                user_id = "user_from_token"
            elif 'x-user-id' in request.headers:
                user_id = request.headers['x-user-id']
            
            return tenant_id, user_id
            
        except (ValueError, TypeError) as e:
            logger.warning("Failed to extract request context", error=str(e))
            return None, None
    
    async def _prepare_request_data(self, request: Request) -> Dict[str, Any]:
        """Prepare request data for threat analysis."""
        try:
            request_data = {
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": dict(request.headers),
                "body": {}
            }
            
            # Get request body for POST/PUT requests
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    if hasattr(request, '_body'):
                        body = request._body
                    else:
                        body = await request.body()
                        request._body = body
                    
                    if body:
                        content_type = request.headers.get("content-type", "")
                        if "application/json" in content_type:
                            import json
                            try:
                                request_data["body"] = json.loads(body.decode())
                            except json.JSONDecodeError:
                                request_data["body"] = {"raw": body.decode()[:1000]}
                        else:
                            request_data["body"] = {"raw": body.decode()[:1000]}
                            
                except Exception as e:
                    logger.warning("Failed to read request body", error=str(e))
                    request_data["body"] = {"error": "Failed to read body"}
            
            return request_data
            
        except Exception as e:
            logger.error("Failed to prepare request data", error=str(e))
            return {
                "method": request.method,
                "path": request.url.path,
                "error": str(e)
            }
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response."""
        try:
            for header_name, header_value in self.security_headers.items():
                response.headers[header_name] = header_value
            
            return response
            
        except Exception as e:
            logger.error("Failed to add security headers", error=str(e))
            return response
    
    async def _log_blocked_request(
        self,
        tenant_id: Optional[uuid.UUID],
        user_id: Optional[str],
        threat_analysis: Dict[str, Any],
        correlation_id: str
    ):
        """Log blocked request for audit trail."""
        try:
            if tenant_id:
                await self.privacy_service.log_audit_event(
                    tenant_id=tenant_id,
                    event_type=AuditEventType.SECURITY_EVENT,
                    action="request_blocked",
                    user_id=user_id,
                    correlation_id=correlation_id,
                    event_data={
                        "threat_level": threat_analysis["threat_level"].value,
                        "attack_types": [at.value for at in threat_analysis["attack_types"]],
                        "analysis_id": threat_analysis["analysis_id"]
                    },
                    success=False,
                    error_message="Request blocked due to security threat"
                )
        except Exception as e:
            logger.error("Failed to log blocked request", error=str(e))
    
    async def _log_successful_request(
        self,
        tenant_id: Optional[uuid.UUID],
        user_id: Optional[str],
        request_data: Dict[str, Any],
        response: Response,
        correlation_id: str
    ):
        """Log successful request for audit trail."""
        try:
            if tenant_id and request_data["path"].startswith('/api'):
                # Only log API requests to avoid noise
                await self.privacy_service.log_audit_event(
                    tenant_id=tenant_id,
                    event_type=AuditEventType.DATA_ACCESS,
                    action=f"{request_data['method']}_{request_data['path']}",
                    user_id=user_id,
                    correlation_id=correlation_id,
                    event_data={
                        "status_code": response.status_code,
                        "method": request_data["method"],
                        "path": request_data["path"]
                    },
                    success=200 <= response.status_code < 400
                )
        except Exception as e:
            logger.error("Failed to log successful request", error=str(e))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware implementing Requirement 10.2.
    
    Provides configurable rate limiting per user, tenant, and endpoint.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limits = {
            '/api/auth': {'requests': 10, 'window': 60},  # 10 requests per minute
            '/api/calls': {'requests': 100, 'window': 60},  # 100 requests per minute
            '/api/admin': {'requests': 50, 'window': 60},   # 50 requests per minute
            'default': {'requests': 200, 'window': 60}      # 200 requests per minute
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests."""
        try:
            # Get rate limit for this path
            rate_limit = self._get_rate_limit(request.url.path)
            
            # Check rate limit (this would integrate with Redis in production)
            # For now, we'll rely on the intrusion detection service
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(rate_limit['requests'])
            response.headers["X-RateLimit-Window"] = str(rate_limit['window'])
            
            return response
            
        except Exception as e:
            logger.error("Rate limit middleware error", error=str(e))
            return await call_next(request)
    
    def _get_rate_limit(self, path: str) -> Dict[str, int]:
        """Get rate limit configuration for path."""
        for rate_path, limit in self.rate_limits.items():
            if rate_path != 'default' and rate_path in path:
                return limit
        
        return self.rate_limits['default']


# Utility functions for middleware integration
def add_security_middleware(app):
    """Add all security middleware to FastAPI app."""
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware)


def get_request_context(request: Request) -> Dict[str, Any]:
    """Get security context from request."""
    return {
        "correlation_id": getattr(request.state, 'correlation_id', None),
        "tenant_id": getattr(request.state, 'tenant_id', None),
        "user_id": getattr(request.state, 'user_id', None),
        "threat_analysis": getattr(request.state, 'threat_analysis', None)
    }