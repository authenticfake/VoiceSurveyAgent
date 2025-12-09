"""
FastAPI application entry point.

REQ-018: Campaign CSV export
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.dashboard.router import export_router, router as dashboard_router
from app.shared.config import get_settings
from app.shared.exceptions import AppException

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting VoiceSurveyAgent API")
    yield
    logger.info("Shutting down VoiceSurveyAgent API")


app = FastAPI(
    title="VoiceSurveyAgent API",
    description="AI-driven outbound phone survey system",
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


# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


# Include routers
app.include_router(dashboard_router)
app.include_router(export_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}