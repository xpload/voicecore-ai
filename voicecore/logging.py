"""
Structured logging configuration for VoiceCore AI.

This module provides comprehensive logging with structured output,
correlation IDs, and security-compliant logging (no PII/location data).
"""

import logging
import sys
from typing import Any, Dict, Optional
from datetime import datetime
import structlog
from rich.console import Console
from rich.logging import RichHandler

from voicecore.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            add_correlation_id,
            sanitize_sensitive_data,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                show_time=False,
                show_path=False,
                markup=True,
            ) if settings.debug else logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set third-party library log levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def add_correlation_id(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add correlation ID to log entries for request tracing."""
    # This will be populated by middleware in actual requests
    correlation_id = getattr(logger, '_correlation_id', None)
    if correlation_id:
        event_dict['correlation_id'] = correlation_id
    return event_dict


def sanitize_sensitive_data(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive data from log entries.
    
    CRITICAL: This ensures no IP addresses, geolocation, or PII is logged
    as per security requirements.
    """
    sensitive_keys = [
        'ip', 'ip_address', 'client_ip', 'remote_addr',
        'geolocation', 'location', 'coordinates', 'lat', 'lng',
        'password', 'token', 'secret', 'key', 'auth',
        'ssn', 'social_security', 'credit_card', 'phone_number'
    ]
    
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary data."""
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key contains sensitive information
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    sanitize_dict(item) if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    # Sanitize the event dictionary
    return sanitize_dict(event_dict)


class VoiceCoreLogger:
    """
    Enhanced logger for VoiceCore AI with security and debugging features.
    
    This logger provides:
    - Structured logging with correlation IDs
    - Security-compliant data sanitization
    - Call flow tracking
    - Performance monitoring
    - Error categorization for rapid debugging
    """
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
        self._correlation_id: Optional[str] = None
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for request tracing."""
        self._correlation_id = correlation_id
        self.logger._correlation_id = correlation_id
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with context."""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context."""
        self.logger.critical(message, **kwargs)
    
    # Specialized logging methods for VoiceCore AI
    
    def call_started(self, call_sid: str, tenant_id: str, from_number: str, **kwargs) -> None:
        """Log call initiation."""
        self.info(
            "Call started",
            call_sid=call_sid,
            tenant_id=tenant_id,
            from_number=from_number,
            event_type="call_started",
            **kwargs
        )
    
    def call_ended(self, call_sid: str, duration: int, status: str, **kwargs) -> None:
        """Log call completion."""
        self.info(
            "Call ended",
            call_sid=call_sid,
            duration_seconds=duration,
            status=status,
            event_type="call_ended",
            **kwargs
        )
    
    def ai_response(self, call_sid: str, response_time_ms: float, **kwargs) -> None:
        """Log AI response performance."""
        self.info(
            "AI response generated",
            call_sid=call_sid,
            response_time_ms=response_time_ms,
            event_type="ai_response",
            **kwargs
        )
    
    def call_transfer(self, call_sid: str, from_ai: bool, to_agent: str, **kwargs) -> None:
        """Log call transfer events."""
        self.info(
            "Call transferred",
            call_sid=call_sid,
            from_ai=from_ai,
            to_agent=to_agent,
            event_type="call_transfer",
            **kwargs
        )
    
    def spam_detected(self, phone_number: str, spam_score: float, reason: str, **kwargs) -> None:
        """Log spam detection events."""
        self.warning(
            "Spam call detected",
            phone_number=phone_number,
            spam_score=spam_score,
            reason=reason,
            event_type="spam_detected",
            **kwargs
        )
    
    def agent_status_change(self, agent_id: str, old_status: str, new_status: str, **kwargs) -> None:
        """Log agent status changes."""
        self.info(
            "Agent status changed",
            agent_id=agent_id,
            old_status=old_status,
            new_status=new_status,
            event_type="agent_status_change",
            **kwargs
        )
    
    def system_error(self, error_type: str, component: str, error_message: str, **kwargs) -> None:
        """Log system errors with categorization for rapid debugging."""
        self.error(
            "System error occurred",
            error_type=error_type,
            component=component,
            error_message=error_message,
            event_type="system_error",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def external_service_error(self, service: str, operation: str, error_code: str, **kwargs) -> None:
        """Log external service integration errors."""
        self.error(
            "External service error",
            service=service,
            operation=operation,
            error_code=error_code,
            event_type="external_service_error",
            **kwargs
        )
    
    def performance_metric(self, metric_name: str, value: float, unit: str, **kwargs) -> None:
        """Log performance metrics."""
        self.info(
            "Performance metric",
            metric_name=metric_name,
            value=value,
            unit=unit,
            event_type="performance_metric",
            **kwargs
        )


def get_logger(name: str) -> VoiceCoreLogger:
    """Get a VoiceCore logger instance."""
    return VoiceCoreLogger(name)