"""
FastAPI application entry point.

Configures and creates the main application instance.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.middleware import AuthMiddleware
from app.campaigns.router import router as campaigns_router
from app.config import get_settings
from app.shared.exceptions import AppException
from app.shared.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    setup_logging()
    logger.info("Application starting", app_name=settings.app_name, env=settings.app_env)
    yield
    logger.info("Application shutting down")

app = FastAPI(
    title=settings.app_name,
    description="AI-driven outbound phone survey system",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions."""
    logger.warning(
        "Application exception",
        error_code=exc.error_code,
        message=exc.message,
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )

# Include routers
app.include_router(campaigns_router, prefix=settings.api_prefix)

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}