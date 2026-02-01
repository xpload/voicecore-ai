"""
Privacy compliance middleware for VoiceCore AI.

Ensures all HTTP requests comply with privacy requirements by:
- Preventing IP address and geolocation data storage
- Sanitizing request/response data
- Logging privacy-compliant audit events

Implements Requirements 5.1, 5.3, 5.5.
"""

import uuid
import time
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from voicecore.services.privacy_service import PrivacyService, AuditEventType
from voicecore.utils.security import SecurityUtils, sanitize_log_data
from voicecore.logging import get_logger


logger = get_logger(__name__)


class PrivacyComplianceMiddleware(BaseHTTPMiddleware):
    """
    Privacy compliance middleware ensuring Requirements 5.1, 5.3, 5.5.
    
    CRITICAL: This middleware ensures no IP addresses, geolocation,
    or location data is stored or logged anywhere in the system.
    """
    
    def __init__(self, app, privacy_service: Optional[PrivacyService] = None):
        super().__init__(app)
        self.privacy_service = privacy_service or PrivacyService()
        self.security_utils = SecurityUtils()
        
        # Paths that require special privacy handling
        self.sensitive_paths = [
            '/api/calls',
            '/api/agents',
            '/api/analytics',
            '/api/admin',
            '/api/tenant'
        ]
        
        # Headers that must be sanitized or removed
        self.sensitive_headers = [
            'x-forwarded-for',
            'x-real-ip',
            'cf-connecting-ip',
            'x-client-ip',
            'x-forwarded',
            'forwarded-for',
            'forwarded',
            'via'
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with privacy compliance.
        
        CRITICAL: This method ensures no IP addresses or location
        data is stored or logged per Requirements 5.1 and 5.5.
        """
        start_time = time.time()
        correlation_id = self.security_utils.generate_correlation_id()
        
        # Add correlation ID to request state for tracking
        request.state.correlation_id = correlation_id
        
        try:
            # Validate request for privacy compliance
            privacy_validation = await self._validate_request_privacy(request)
            
            if not privacy_validation["compliant"]:
                # Return error for privacy violations
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Privacy compliance violation",
                        "message": "Request contains prohibited data",
                        "correlation_id": correlation_id
                    }
                )
            
            # Sanitize request headers (remove IP-related headers)
            sanitized_headers = self._sanitize_request_headers(dict(request.headers))
            
            # Process request
            response = await call_next(request)
            
            # Sanitize response if needed
            if self._is_sensitive_path(request.url.path):
                response = await self._sanitize_response(response, request)
            
            # Log privacy-compliant audit event
            await self._log_request_audit(
                request=request,
                response=response,
                correlation_id=correlation_id,
                processing_time=time.time() - start_time,
                sanitized_headers=sanitized_headers
            )
            
            # Add privacy compliance headers to response
            response.headers["X-Privacy-Compliant"] = "true"
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            logger.error(
                "Privacy middleware error",
                correlation_id=correlation_id,
                error=str(e),
                path=request.url.path
            )
            
            # Log error event
            if hasattr(request.state, 'tenant_id'):
                await self.privacy_service.log_audit_event(
                    tenant_id=request.state.tenant_id,
                    event_type=AuditEventType.SECURITY_EVENT,
                    action="privacy_middleware_error",
                    correlation_id=correlation_id,
                    event_data={"error": str(e), "path": request.url.path},
                    success=False,
                    error_message=str(e)
                )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "correlation_id": correlation_id
                }
            )
    
    async def _validate_request_privacy(self, request: Request) -> Dict[str, Any]:
        """
        Validate request for privacy compliance.
        
        Ensures no IP addresses, geolocation, or location data
        is present in the request.
        """
        try:
            validation_result = {
                "compliant": True,
                "violations": [],
                "warnings": []
            }
            
            # Check headers for privacy violations
            for header_name, header_value in request.headers.items():
                header_lower = header_name.lower()
                
                # Check for location-related headers
                if any(keyword in header_lower for keyword in ['location', 'geo', 'lat', 'lng', 'coordinates']):
                    validation_result["compliant"] = False
                    validation_result["violations"].append(f"location_header: {header_name}")
                
                # Check for IP-related headers (these will be sanitized but flagged)
                if header_lower in self.sensitive_headers:
                    validation_result["warnings"].append(f"ip_header_sanitized: {header_name}")
            
            # Check query parameters
            for param_name, param_value in request.query_params.items():
                param_lower = param_name.lower()
                
                if any(keyword in param_lower for keyword in ['ip', 'location', 'geo', 'lat', 'lng']):
                    validation_result["compliant"] = False
                    validation_result["violations"].append(f"location_param: {param_name}")
            
            # For POST/PUT requests, check body (if JSON)
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    if hasattr(request, '_body'):
                        # Body already read, use cached version
                        body = request._body
                    else:
                        # Read and cache body
                        body = await request.body()
                        request._body = body
                    
                    if body and request.headers.get("content-type", "").startswith("application/json"):
                        import json
                        try:
                            body_data = json.loads(body.decode())
                            body_violations = self._detect_privacy_violations_in_data(body_data)
                            if body_violations:
                                validation_result["compliant"] = False
                                validation_result["violations"].extend(body_violations)
                        except json.JSONDecodeError:
                            # Not valid JSON, skip validation
                            pass
                            
                except Exception as e:
                    logger.warning("Failed to validate request body", error=str(e))
            
            return validation_result
            
        except Exception as e:
            logger.error("Failed to validate request privacy", error=str(e))
            return {
                "compliant": False,
                "violations": ["validation_error"],
                "warnings": []
            }
    
    def _sanitize_request_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Sanitize request headers to remove IP and location data.
        
        CRITICAL: This ensures no IP addresses are stored per Requirement 5.1.
        """
        sanitized = {}
        
        for header_name, header_value in headers.items():
            header_lower = header_name.lower()
            
            # Remove IP-related headers completely
            if header_lower in self.sensitive_headers:
                sanitized[header_name] = "[REDACTED_IP]"
            # Sanitize user-agent
            elif header_lower == "user-agent":
                sanitized[header_name] = self._sanitize_user_agent(header_value)
            # Keep other headers as-is (they're already validated)
            else:
                sanitized[header_name] = header_value
        
        return sanitized
    
    async def _sanitize_response(self, response: Response, request: Request) -> Response:
        """
        Sanitize response data to ensure privacy compliance.
        """
        try:
            # Only sanitize JSON responses
            if (hasattr(response, 'media_type') and 
                response.media_type == "application/json" and
                hasattr(response, 'body')):
                
                import json
                
                # Get response body
                body = response.body
                if body:
                    try:
                        response_data = json.loads(body.decode())
                        
                        # Sanitize response data
                        sanitized_data = self.security_utils.sanitize_data(response_data)
                        
                        # Create new response with sanitized data
                        new_body = json.dumps(sanitized_data).encode()
                        
                        # Update response
                        response.body = new_body
                        response.headers["content-length"] = str(len(new_body))
                        
                    except json.JSONDecodeError:
                        # Not valid JSON, leave as-is
                        pass
            
            return response
            
        except Exception as e:
            logger.error("Failed to sanitize response", error=str(e))
            return response
    
    async def _log_request_audit(
        self,
        request: Request,
        response: Response,
        correlation_id: str,
        processing_time: float,
        sanitized_headers: Dict[str, str]
    ):
        """
        Log privacy-compliant audit event for the request.
        
        CRITICAL: This method ensures no IP addresses or location
        data is logged per Requirements 5.1 and 5.5.
        """
        try:
            # Get tenant ID if available
            tenant_id = getattr(request.state, 'tenant_id', None)
            
            if not tenant_id:
                # Try to extract from path or headers
                tenant_id = self._extract_tenant_id(request)
            
            if tenant_id:
                # Prepare sanitized event data
                event_data = {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "user_agent": sanitized_headers.get("user-agent", "unknown")[:100],
                    "content_type": request.headers.get("content-type"),
                    "content_length": request.headers.get("content-length")
                }
                
                # Determine event type based on request
                if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
                    event_type = AuditEventType.DATA_MODIFICATION
                else:
                    event_type = AuditEventType.DATA_ACCESS
                
                # Log audit event
                await self.privacy_service.log_audit_event(
                    tenant_id=uuid.UUID(tenant_id),
                    event_type=event_type,
                    action=f"{request.method}_{request.url.path}",
                    correlation_id=correlation_id,
                    event_data=event_data,
                    success=200 <= response.status_code < 400,
                    user_agent=sanitized_headers.get("user-agent")
                )
                
        except Exception as e:
            logger.error(
                "Failed to log request audit",
                correlation_id=correlation_id,
                error=str(e)
            )
    
    def _is_sensitive_path(self, path: str) -> bool:
        """Check if path requires special privacy handling."""
        return any(sensitive_path in path for sensitive_path in self.sensitive_paths)
    
    def _detect_privacy_violations_in_data(self, data: Any) -> List[str]:
        """Detect privacy violations in request/response data."""
        violations = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                key_lower = key.lower()
                
                # Check for location-related keys
                location_keywords = ['ip', 'latitude', 'longitude', 'lat', 'lng', 'coordinates', 
                                   'geolocation', 'location', 'address', 'city', 'state', 'country']
                
                if any(keyword in key_lower for keyword in location_keywords):
                    violations.append(f"location_data_key: {key}")
                
                # Recursively check nested data
                if isinstance(value, (dict, list)):
                    violations.extend(self._detect_privacy_violations_in_data(value))
                elif isinstance(value, str):
                    # Check for IP patterns in string values
                    import re
                    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                    if re.search(ip_pattern, value):
                        violations.append(f"ip_address_in_value: {key}")
        
        elif isinstance(data, list):
            for item in data:
                violations.extend(self._detect_privacy_violations_in_data(item))
        
        return violations
    
    def _sanitize_user_agent(self, user_agent: str) -> str:
        """Sanitize user agent string."""
        if not user_agent:
            return "unknown"
        
        # Remove version numbers and specific identifiers
        import re
        sanitized = re.sub(r'\d+\.\d+[\.\d]*', 'X.X', user_agent)
        sanitized = re.sub(r'\([^)]*\)', '(sanitized)', sanitized)
        
        return sanitized[:200]  # Limit length
    
    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request for audit logging."""
        try:
            # Try to get from path parameters
            if hasattr(request, 'path_params') and 'tenant_id' in request.path_params:
                return request.path_params['tenant_id']
            
            # Try to get from query parameters
            if 'tenant_id' in request.query_params:
                return request.query_params['tenant_id']
            
            # Try to get from headers
            if 'x-tenant-id' in request.headers:
                return request.headers['x-tenant-id']
            
            return None
            
        except Exception:
            return None


class DataEncryptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic data encryption per Requirement 5.3.
    
    Encrypts sensitive data in requests and decrypts in responses
    for specific endpoints that handle sensitive information.
    """
    
    def __init__(self, app, privacy_service: Optional[PrivacyService] = None):
        super().__init__(app)
        self.privacy_service = privacy_service or PrivacyService()
        
        # Endpoints that require automatic encryption
        self.encryption_endpoints = [
            '/api/calls',
            '/api/agents/profile',
            '/api/tenant/settings'
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with automatic encryption/decryption."""
        try:
            # Check if this endpoint requires encryption
            if self._requires_encryption(request.url.path):
                # For POST/PUT requests, encrypt sensitive data
                if request.method in ["POST", "PUT", "PATCH"]:
                    await self._encrypt_request_data(request)
            
            # Process request
            response = await call_next(request)
            
            # For GET requests on encrypted endpoints, decrypt response data
            if (request.method == "GET" and 
                self._requires_encryption(request.url.path) and
                hasattr(request.state, 'tenant_id')):
                
                response = await self._decrypt_response_data(response, request.state.tenant_id)
            
            return response
            
        except Exception as e:
            logger.error("Data encryption middleware error", error=str(e))
            return await call_next(request)
    
    def _requires_encryption(self, path: str) -> bool:
        """Check if path requires automatic encryption."""
        return any(endpoint in path for endpoint in self.encryption_endpoints)
    
    async def _encrypt_request_data(self, request: Request):
        """Encrypt sensitive data in request."""
        try:
            if hasattr(request.state, 'tenant_id') and hasattr(request, '_body'):
                body = request._body
                if body and request.headers.get("content-type", "").startswith("application/json"):
                    import json
                    try:
                        body_data = json.loads(body.decode())
                        
                        # Encrypt sensitive fields
                        encrypted_data = await self.privacy_service.encrypt_call_data(
                            tenant_id=request.state.tenant_id,
                            call_data=body_data
                        )
                        
                        # Update request body
                        new_body = json.dumps(encrypted_data).encode()
                        request._body = new_body
                        
                    except json.JSONDecodeError:
                        pass  # Not valid JSON
                        
        except Exception as e:
            logger.error("Failed to encrypt request data", error=str(e))
    
    async def _decrypt_response_data(self, response: Response, tenant_id: uuid.UUID) -> Response:
        """Decrypt sensitive data in response."""
        try:
            if (hasattr(response, 'media_type') and 
                response.media_type == "application/json" and
                hasattr(response, 'body')):
                
                import json
                
                body = response.body
                if body:
                    try:
                        response_data = json.loads(body.decode())
                        
                        # Decrypt sensitive fields
                        decrypted_data = await self.privacy_service.decrypt_call_data(
                            tenant_id=tenant_id,
                            encrypted_call_data=response_data
                        )
                        
                        # Update response
                        new_body = json.dumps(decrypted_data).encode()
                        response.body = new_body
                        response.headers["content-length"] = str(len(new_body))
                        
                    except json.JSONDecodeError:
                        pass  # Not valid JSON
            
            return response
            
        except Exception as e:
            logger.error("Failed to decrypt response data", error=str(e))
            return response


# Utility functions for middleware integration
def add_privacy_middleware(app):
    """Add privacy compliance middleware to FastAPI app."""
    app.add_middleware(PrivacyComplianceMiddleware)
    app.add_middleware(DataEncryptionMiddleware)


def get_correlation_id(request: Request) -> Optional[str]:
    """Get correlation ID from request state."""
    return getattr(request.state, 'correlation_id', None)