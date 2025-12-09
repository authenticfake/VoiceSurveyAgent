"""
FastAPI application entry point.

REQ-002: OIDC authentication integration
REQ-003: RBAC authorization middleware
REQ-004: Campaign CRUD API
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.campaigns.router import router as campaigns_router
from app.config import get_settings
from app.shared.database import db_manager
from app.shared.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    setup_logging()
    logger.info("Starting application")
    yield
    logger.info("Shutting down application")
    await db_manager.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="VoiceSurveyAgent API",
        description="AI-driven outbound phone survey system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(auth_router)
    app.include_router(campaigns_router)

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle validation errors."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            })

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "errors": errors,
                }
            },
        )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()