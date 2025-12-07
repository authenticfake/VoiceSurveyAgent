from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.http.auth.router import router as auth_router
from app.infra.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize database structures on application startup."""
    await init_db()
    yield


def create_app() -> FastAPI:
    """Factory to create a FastAPI instance with all routers mounted."""
    application = FastAPI(
        title="Voice Survey Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(auth_router)
    return application


app = create_app()