"""FastAPI application entry point."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.http.auth import router as auth_router
from app.api.http.protected import router as protected_router
from app.auth.oidc import OIDCClient, OIDCConfig
from app.auth.repository import InMemoryUserRepository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Initialize OIDC client
    oidc_config = OIDCConfig(
        issuer=os.getenv("OIDC_ISSUER", "https://example.auth0.com/"),
        client_id=os.getenv("OIDC_CLIENT_ID", "test-client-id"),
        client_secret=os.getenv("OIDC_CLIENT_SECRET", "test-client-secret"),
        redirect_uri=os.getenv("OIDC_REDIRECT_URI", "http://localhost:8000/api/auth/callback"),
    )

    oidc_client = OIDCClient(oidc_config)

    # Try to discover OIDC endpoints (skip in test mode)
    if os.getenv("SKIP_OIDC_DISCOVERY", "false").lower() != "true":
        try:
            await oidc_client.discover()
        except Exception:
            # Log warning but don't fail startup
            pass

    app.state.oidc_client = oidc_client
    app.state.user_repository = InMemoryUserRepository()

    yield

    # Cleanup if needed


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Voice Survey Agent API",
        description="AI-driven outbound phone survey system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(protected_router, prefix="/api")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()