from fastapi import FastAPI

from app.api.http.campaigns.router import router as campaigns_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Voice Survey Agent API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(campaigns_router)
    return app


app = create_app()