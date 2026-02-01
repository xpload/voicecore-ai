"""
Custom middleware for VoiceCore AI application.

This module provides security, tenant isolation, rate limiting,
and request tracking middleware with enterprise-grade features.
"""

import time
import uuid
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
import aioredis

from voicecore.config import settings
from voicecore.logging import get_logger


logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to all requests for tracing.
    
    This enables end-to-end request tracking across all services
    and logs for debugging and monitoring purposes.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        
        # Store in request state
        request.state.correlation_id = correlation_id
        
        # Set logger correlation ID
        logger.set_correlation_id(correlation_id)
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log request completion
        logger.info(
            "Request completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2),
            correlation_id=correlation_id
        )
        
        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant context from requests.
    
    This ensures proper tenant isolation and sets the database
    context for Row-Level Security (RLS) policies.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract tenant ID from various sources
        tenant_id = self._extract_tenant_id(request)
        
        if tenant_id:
            # Validate tenant exists and is active
            try:
                from voicecore.services.tenant_service import TenantService
                tenant_service = TenantService()
                tenant_info = await tenant_service.get_tenant(tenant_id)
                
                if tenant_info and tenant_info.get('is_active', False):
                    request.state.tenant_id = tenant_id
                    request.state.tenant_name = tenant_info.get('name')
                    
                    logger.debug(
                        "Tenant context set",
                        tenant_id=tenant_id,
                        tenant_name=tenant_info.get('name'),
                        correlation_id=getattr(request.state, 'correlation_id', None)
                    )
                else:
                    logger.warning(
                        "Invalid or inactive tenant",
                        tenant_id=tenant_id,
                        correlation_id=getattr(request.state, 'correlation_id', None)
                    )
            except Exception as e:
                logger.error(
                    "Failed to validate tenant",
                    tenant_id=tenant_id,
                    error=str(e),
                    correlation_id=getattr(request.state, 'correlation_id', None)
                )
        
        return await call_next(request)
    
    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """
        Extract tenant ID from request headers, subdomain, or JWT token.
        
        Priority order:
        1. X-Tenant-ID header
        2. Subdomain extraction
        3. JWT token claims
        """
        # Check header first
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # Extract from subdomain
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain and subdomain != "www" and subdomain != "api":
                return subdomain
        
        # TODO: Extract from JWT token if present
        
        return None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Implements enterprise security best practices including
    HSTS, CSP, and other protective headers.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' wss: https:; "
                "font-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        }
        
        # Add HSTS in production
        if not settings.debug:
            security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Apply headers
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests per IP/tenant.
    
    Uses Redis for distributed rate limiting across multiple
    application instances with sliding window algorithm.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.redis: Optional[aioredis.Redis] = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and internal endpoints
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Initialize Redis connection if needed
        if not self.redis:
            try:
                self.redis = aioredis.from_url(settings.redis_url)
            except Exception as e:
                logger.warning("Redis not available for rate limiting", error=str(e))
                return await call_next(request)
        
        # Determine rate limit key (prefer tenant over IP for security)
        tenant_id = getattr(request.state, 'tenant_id', None)
        if tenant_id:
            rate_limit_key = f"rate_limit:tenant:{tenant_id}"
        else:
            # Use a generic key for unauthenticated requests
            rate_limit_key = "rate_limit:anonymous"
        
        # Check rate limit
        try:
            current_requests = await self._check_rate_limit(rate_limit_key)
            
            if current_requests > settings.rate_limit_calls_per_minute:
                logger.warning(
                    "Rate limit exceeded",
                    key=rate_limit_key,
                    current_requests=current_requests,
                    limit=settings.rate_limit_calls_per_minute
                )
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": 60
                    },
                    headers={"Retry-After": "60"}
                )
            
        except Exception as e:
            logger.error("Rate limiting error", error=str(e))
            # Continue without rate limiting if Redis fails
        
        return await call_next(request)
    
    async def _check_rate_limit(self, key: str) -> int:
        """
        Check and update rate limit using sliding window algorithm.
        
        Returns:
            int: Current request count in the window
        """
        now = int(time.time())
        window_start = now - 60  # 1-minute window
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Add current request
        pipe.zadd(key, {str(uuid.uuid4()): now})
        
        # Count requests in window
        pipe.zcard(key)
        
        # Set expiration
        pipe.expire(key, 120)  # Keep data for 2 minutes
        
        results = await pipe.execute()
        return results[2]  # Request count


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging.
    
    Logs all API requests with security-compliant data sanitization.
    Does NOT log IP addresses or location data per security requirements.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request start (without sensitive data)
        logger.info(
            "Request started",
            method=request.method,
            path=str(request.url.path),
            query_params=dict(request.query_params),
            user_agent=request.headers.get("user-agent", "unknown"),
            content_type=request.headers.get("content-type"),
            tenant_id=getattr(request.state, 'tenant_id', None),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log request completion
        logger.info(
            "Request completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2),
            response_size=response.headers.get("content-length", "unknown"),
            tenant_id=getattr(request.state, 'tenant_id', None),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )
        
        return response