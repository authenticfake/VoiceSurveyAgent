from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.auth.dependencies import get_current_user, get_oidc_client, get_token_service
from app.auth.router import router as auth_router
from app.config import get_settings
from app.shared.database import init_engine
from app.shared.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, title="Voice Survey Auth API")
    app.include_router(auth_router)

    @app.get("/api/protected")
    async def protected_route(user: User = Depends(get_current_user)):
        return {"message": f"Hello {user.name}"}

    @app.get("/healthz")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()