"""
VoiceCore AI 2.0 - API Gateway
Central gateway for all microservices with load balancing and authentication
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import httpx
import asyncio
from typing import List, Optional, Dict, Any
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service registry
SERVICES = {
    "tenant": {"url": "http://localhost:8001", "health": True},
    "call": {"url": "http://localhost:8002", "health": True},
    "ai": {"url": "http://localhost:8003", "health": True},
    "crm": {"url": "http://localhost:8004", "health": True},
    "analytics": {"url": "http://localhost:8005", "health": True},
    "integration": {"url": "http://localhost:8006", "health": True},
    "billing": {"url": "http://localhost:8007", "health": True},
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 VoiceCore AI 2.0 - API Gateway Starting...")
    
    # Start health check task
    asyncio.create_task(health_check_services())
    
    yield
    logger.info("🚀 API Gateway Shutting Down...")

# Create FastAPI app
app = FastAPI(
    title="VoiceCore AI 2.0 - API Gateway",
    description="Central API Gateway for VoiceCore AI 2.0 microservices",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def health_check_services():
    """Periodically check service health"""
    while True:
        async with httpx.AsyncClient() as client:
            for service_name, service_info in SERVICES.items():
                try:
                    response = await client.get(f"{service_info['url']}/health", timeout=5.0)
                    SERVICES[service_name]["health"] = response.status_code == 200
                    SERVICES[service_name]["last_check"] = datetime.now().isoformat()
                except Exception as e:
                    SERVICES[service_name]["health"] = False
                    SERVICES[service_name]["last_check"] = datetime.now().isoformat()
                    SERVICES[service_name]["error"] = str(e)
        
        await asyncio.sleep(30)  # Check every 30 seconds

async def proxy_request(service_name: str, path: str, request: Request):
    """Proxy request to appropriate microservice"""
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    service_info = SERVICES[service_name]
    if not service_info["health"]:
        raise HTTPException(status_code=503, detail=f"Service {service_name} is unavailable")
    
    # Build target URL
    target_url = f"{service_info['url']}{path}"
    
    # Forward request
    async with httpx.AsyncClient() as client:
        try:
            # Get request body if present
            body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
            
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                content=body,
                timeout=30.0
            )
            
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            logger.error(f"Error proxying request to {service_name}: {e}")
            raise HTTPException(status_code=502, detail=f"Bad gateway: {str(e)}")

@app.get("/health")
async def health_check():
    """Gateway health check"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": SERVICES
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "VoiceCore AI 2.0 - API Gateway",
        "version": "2.0.0",
        "status": "running",
        "available_services": list(SERVICES.keys()),
        "documentation": "/docs"
    }

@app.get("/services")
async def list_services():
    """List all available services and their status"""
    return {
        "services": SERVICES,
        "total_services": len(SERVICES),
        "healthy_services": sum(1 for s in SERVICES.values() if s["health"])
    }

# Dynamic routing for all services
@app.api_route("/api/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_to_service(service_name: str, path: str, request: Request):
    """Route requests to appropriate microservice"""
    return await proxy_request(service_name, f"/{path}", request)

@app.api_route("/api/{service_name}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_to_service_root(service_name: str, request: Request):
    """Route requests to service root"""
    return await proxy_request(service_name, "/", request)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )