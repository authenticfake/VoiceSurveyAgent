"""
FastAPI application entry point.

Configures and creates the main application instance.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.config import get_settings
from app.shared.exceptions import AppError
from app.shared.logging import configure_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    configure_logging()
    logger.info(
        "Application starting",
        app_name=settings.app_name,
        environment=settings.environment,
    )
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
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


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle application errors."""
    logger.warning(
        "Application error",
        error_code=exc.code,
        error_message=exc.message,
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


# Include routers
app.include_router(auth_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}