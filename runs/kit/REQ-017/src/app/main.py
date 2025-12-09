"""
FastAPI application entry point.

REQ-017: Campaign dashboard stats API
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dashboard.router import router as dashboard_router
from app.shared.cache import get_cache_client
from app.shared.config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting VoiceSurveyAgent Dashboard API")
    cache_client = get_cache_client()
    await cache_client.connect()
    yield
    # Shutdown
    logger.info("Shutting down VoiceSurveyAgent Dashboard API")
    await cache_client.disconnect()


app = FastAPI(
    title="VoiceSurveyAgent Dashboard API",
    description="Campaign statistics and dashboard API for VoiceSurveyAgent",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dashboard_router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}