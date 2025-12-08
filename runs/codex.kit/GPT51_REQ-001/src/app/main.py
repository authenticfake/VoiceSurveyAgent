from __future__ import annotations

from fastapi import FastAPI

from app.api.http.auth.routes import router as auth_router


def create_app() -> FastAPI:
    """Application factory.

    REQ‑001 only wires the auth router; other REQs will extend this.
    """
    app = FastAPI(title="voicesurveyagent API")

    app.include_router(auth_router)

    return app


app = create_app()