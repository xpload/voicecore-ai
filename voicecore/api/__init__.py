"""
VoiceCore AI API Routes.

This module contains all API route definitions organized by functional domain.
Each module contains FastAPI routers for specific functionality.
"""

from .tenant_routes import router as tenant_router

# API router imports
__all__ = [
    "tenant_router"
]