"""
VoiceCore AI 2.0 - Billing Service
Advanced billing and subscription management
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("💳 VoiceCore AI 2.0 - Billing Service Starting...")
    yield
    logger.info("💳 Billing Service Shutting Down...")

# Create FastAPI app
app = FastAPI(
    title="VoiceCore AI 2.0 - Billing Service",
    description="Advanced billing and subscription management service",
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "billing-service",
        "version": "2.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "VoiceCore AI 2.0 - Billing Service",
        "version": "2.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8007))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )