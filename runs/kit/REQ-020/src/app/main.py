"""
FastAPI application entry point for REQ-020.

Demonstrates how to wire up the calls router.
"""

from fastapi import FastAPI

from app.calls.router import router as calls_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="VoiceSurveyAgent API",
        description="AI-driven outbound phone survey system",
        version="0.1.0",
    )
    
    # Include routers
    app.include_router(calls_router)
    
    return app


app = create_app()