"""
VoiceCore AI - Production Application
Tech Startup Dashboard Integration

Complete enterprise virtual receptionist system with GitHub-inspired dark interface.
"""

import os
import sys
import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import VoiceCore modules
from voicecore.main import create_app
from voicecore.config import get_settings
from voicecore.logging import get_logger

# Import Tech Startup Dashboard
from dashboard_tech_startup_complete import create_tech_startup_dashboard_app

logger = get_logger(__name__)
settings = get_settings()

def create_production_app() -> FastAPI:
    """Create the production FastAPI application with Tech Startup dashboard."""
    
    # Create main VoiceCore app
    main_app = create_app()
    
    # Create Tech Startup dashboard app
    dashboard_app = create_tech_startup_dashboard_app()
    
    # Create production app
    app = FastAPI(
        title="VoiceCore AI - Enterprise Platform",
        description="Complete Virtual Receptionist System with Tech Startup Dashboard",
        version="3.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    if os.path.exists("voicecore/static"):
        app.mount("/static", StaticFiles(directory="voicecore/static"), name="static")
    
    # Root redirect to dashboard
    @app.get("/", response_class=RedirectResponse)
    async def root():
        return RedirectResponse(url="/dashboard")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "VoiceCore AI Enterprise",
            "dashboard": "Tech Startup",
            "version": "3.0.0"
        }
    
    # Mount dashboard routes
    app.mount("/dashboard", dashboard_app, name="dashboard")
    
    # Mount main API routes
    app.mount("/api", main_app, name="api")
    
    return app

# Create the application instance
app = create_production_app()

if __name__ == "__main__":
    print("🚀 Starting VoiceCore AI Enterprise Platform with Tech Startup Dashboard")
    print("📊 Dashboard: GitHub-Inspired Dark Professional Interface")
    print("🌐 Access: http://localhost:8000/dashboard")
    
    uvicorn.run(
        "simple_start:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        log_level="info"
    )
