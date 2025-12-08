"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.config import get_settings
from app.shared.database import close_db
from app.shared.exceptions import AppException
from app.shared.logging import setup_logging, get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    setup_logging()
    logger.info("Application starting up")
    yield
    # Shutdown
    logger.info("Application shutting down")
    await close_db()

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="VoiceSurveyAgent API",
        description="AI-driven outbound phone survey system",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
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
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    # Include routers
    app.include_router(auth_router)

    # Health check
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    return app

app = create_app()