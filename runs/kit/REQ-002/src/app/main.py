"""
FastAPI application entry point.

REQ-002: OIDC authentication integration
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.config import get_settings
from app.shared.database import get_database_manager
from app.shared.exceptions import AppException
from app.shared.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    setup_logging()
    logger.info("Application starting", extra={"env": get_settings().app_env})

    yield

    # Cleanup
    await get_database_manager().close()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="VoiceSurveyAgent API",
        description="AI-driven outbound phone survey system",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        """Handle application exceptions."""
        logger.error(
            exc.message,
            extra={"code": exc.code, "details": exc.details, "path": request.url.path},
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    # Include routers
    app.include_router(auth_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


# Application instance
app = create_app()