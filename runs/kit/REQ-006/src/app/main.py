from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.contacts.router import router as contacts_router
from app.shared.exceptions import NotFoundError, ValidationError

# Register models for SQLAlchemy metadata during tests
import app.email.models  # noqa: F401


def create_app() -> FastAPI:
    app = FastAPI(title="VoiceSurveyAgent")

    # Map domain exceptions to HTTP responses (needed by router tests)
    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # IMPORTANT:
    # contacts_router already has prefix="/api/campaigns"
    # so we must NOT add another prefix here.
    app.include_router(contacts_router)

    return app


app = create_app()
