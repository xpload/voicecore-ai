"""
VoiceCore AI - Main application entry point.

This module initializes the FastAPI application with all necessary
middleware, routers, and configurations for the enterprise virtual
receptionist system.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

from voicecore.config import settings
from voicecore.logging import configure_logging, get_logger
from voicecore.database import init_database, close_database
from voicecore.middleware import (
    CorrelationIDMiddleware,
    TenantContextMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware
)


# Configure logging before any other imports
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for database connections,
    external service initialization, and cleanup.
    """
    logger.info("Starting VoiceCore AI application", version=settings.app_version)
    
    try:
        # Initialize database connections
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize WebSocket manager
        from voicecore.services.websocket_service import websocket_manager
        await websocket_manager.start()
        logger.info("WebSocket manager initialized successfully")
        
        # Initialize task scheduler for analytics
        from voicecore.services.scheduler_service import scheduler
        from voicecore.services.analytics_service import AnalyticsService
        
        await scheduler.start()
        
        # Schedule automatic metrics collection every 5 minutes
        analytics_service = AnalyticsService()
        scheduler.schedule_task(
            "collect_system_metrics",
            analytics_service.collect_system_metrics,
            300  # 5 minutes
        )
        
        # Schedule call analytics collection every 10 minutes
        scheduler.schedule_task(
            "collect_call_analytics",
            analytics_service.collect_call_analytics,
            600  # 10 minutes
        )
        
        logger.info("Analytics scheduler initialized successfully")
        
        # Initialize external services
        # TODO: Initialize Twilio, OpenAI, Redis connections
        
        logger.info("VoiceCore AI startup completed successfully")
        yield
        
    except Exception as e:
        logger.critical("Failed to start VoiceCore AI", error=str(e))
        raise
    
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down VoiceCore AI")
        
        # Stop WebSocket manager
        from voicecore.services.websocket_service import websocket_manager
        await websocket_manager.stop()
        
        # Stop task scheduler
        from voicecore.services.scheduler_service import scheduler
        await scheduler.stop()
        
        await close_database()
        logger.info("VoiceCore AI shutdown completed")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    
    app = FastAPI(
        title=settings.app_name,
        description="Enterprise Virtual Receptionist System - Multitenant AI-Powered Call Management",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Add security middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware for security
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure with actual domains in production
        )
    
    # Add custom middleware
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Add exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Global exception handler with comprehensive error reporting."""
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        tenant_id = getattr(request.state, 'tenant_id', None)
        
        # Import error handling service
        from voicecore.services.error_handling_service import (
            error_handling_service, SystemComponent, ErrorCategory, ErrorSeverity
        )
        
        # Determine error severity based on exception type
        if isinstance(exc, (ConnectionError, TimeoutError)):
            severity = ErrorSeverity.HIGH
            category = ErrorCategory.NETWORK
        elif isinstance(exc, PermissionError):
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.AUTHENTICATION
        elif isinstance(exc, ValueError):
            severity = ErrorSeverity.LOW
            category = ErrorCategory.VALIDATION
        else:
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.SYSTEM
        
        # Report error to error handling service
        try:
            await error_handling_service.report_error(
                component=SystemComponent.API_GATEWAY,
                category=category,
                severity=severity,
                error=exc,
                context={
                    "request_url": str(request.url),
                    "request_headers": dict(request.headers),
                    "user_agent": request.headers.get("user-agent")
                },
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                request_path=str(request.url.path),
                request_method=request.method
            )
        except Exception as report_error:
            # Fallback logging if error reporting fails
            logger.critical(
                "Error reporting system failure",
                original_error=str(exc),
                reporting_error=str(report_error),
                correlation_id=correlation_id
            )
        
        # Log error with structured data
        logger.system_error(
            error_type=type(exc).__name__,
            component="global_handler",
            error_message=str(exc),
            correlation_id=correlation_id,
            path=str(request.url.path),
            method=request.method
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "correlation_id": correlation_id,
                "message": "An unexpected error occurred. Please contact support."
            }
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        """Enhanced health check endpoint with system monitoring."""
        try:
            # Import error handling service
            from voicecore.services.error_handling_service import error_handling_service
            
            # Get basic health status
            basic_health = {
                "status": "healthy",
                "service": settings.app_name,
                "version": settings.app_version,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get comprehensive system health
            try:
                system_health = await error_handling_service.get_system_health()
                basic_health["system_status"] = system_health["overall_status"]
                basic_health["components"] = len(system_health.get("components", {}))
                basic_health["critical_issues"] = len(system_health.get("critical_issues", []))
            except Exception as e:
                logger.warning("Failed to get system health for health check", error=str(e))
                basic_health["system_status"] = "unknown"
            
            return basic_health
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "service": settings.app_name,
                "version": settings.app_version,
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Health check failed"
            }
    
    # Root endpoint
    @app.get("/")
    async def root() -> dict:
        """Root endpoint with basic service information."""
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "description": "Enterprise Virtual Receptionist System",
            "status": "operational"
        }
    
    # Register API routers
    from voicecore.api.tenant_routes import router as tenant_router
    from voicecore.api.webhook_routes import router as webhook_router
    from voicecore.api.agent_routes import router as agent_router
    from voicecore.api.websocket_routes import router as websocket_router
    from voicecore.api.call_logging_routes import router as call_logging_router
    from voicecore.api.pwa_routes import router as pwa_router
    from voicecore.api.admin_routes import router as admin_router
    from voicecore.api.tenant_admin_routes import router as tenant_admin_router
    from voicecore.api.voicemail_routes import router as voicemail_router
    from voicecore.api.vip_routes import router as vip_router
    from voicecore.api.callback_routes import router as callback_router
    from voicecore.api.analytics_routes import router as analytics_router
    from voicecore.api.ai_training_routes import router as ai_training_router
    from voicecore.api.learning_feedback_routes import router as learning_feedback_router
    from voicecore.api.emotion_detection_routes import router as emotion_detection_router
    from voicecore.api.data_export_routes import router as data_export_router
    from voicecore.api.credit_routes import router as credit_router
    from voicecore.api.error_handling_routes import router as error_handling_router
    from voicecore.api.bi_dashboard_routes import router as bi_dashboard_router
    from voicecore.api.report_builder_routes import router as report_builder_router
    from voicecore.api.event_sourcing_routes import router as event_sourcing_router
    
    app.include_router(tenant_router, tags=["Tenants"])
    app.include_router(webhook_router, tags=["Webhooks"])
    app.include_router(agent_router, tags=["Agents"])
    app.include_router(websocket_router, tags=["WebSocket"])
    app.include_router(call_logging_router, tags=["Call Logging"])
    app.include_router(pwa_router, tags=["PWA"])
    app.include_router(admin_router, tags=["Super Admin"])
    app.include_router(tenant_admin_router, tags=["Tenant Admin"])
    app.include_router(voicemail_router, tags=["Voicemail"])
    app.include_router(vip_router, tags=["VIP Management"])
    app.include_router(callback_router, tags=["Callback Management"])
    app.include_router(analytics_router, tags=["Analytics"])
    app.include_router(ai_training_router, tags=["AI Training"])
    app.include_router(learning_feedback_router, tags=["Learning & Feedback"])
    app.include_router(emotion_detection_router, tags=["Emotion Detection"])
    app.include_router(data_export_router, tags=["Data Export & Integration"])
    app.include_router(credit_router, tags=["Credit Management & Billing"])
    app.include_router(error_handling_router, tags=["System Diagnostics & Error Handling"])
    app.include_router(bi_dashboard_router, tags=["Business Intelligence"])
    app.include_router(report_builder_router, tags=["Report Builder"])
    app.include_router(event_sourcing_router, tags=["Event Sourcing & CQRS"])
    
    # TODO: Add other routers as they are implemented
    # app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    # app.include_router(calls_router, prefix="/api/v1/calls", tags=["Calls"])
    # app.include_router(admin_router, prefix="/api/v1/admin", tags=["Administration"])
    
    logger.info("FastAPI application created successfully")
    return app


# Create the application instance
app = create_application()


def main() -> None:
    """Main entry point for running the application."""
    logger.info(
        "Starting VoiceCore AI server",
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
        reload=settings.reload
    )
    
    uvicorn.run(
        "voicecore.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_config=None,  # Use our custom logging configuration
        access_log=False,  # Disable uvicorn access logs (we handle this in middleware)
    )


if __name__ == "__main__":
    main()