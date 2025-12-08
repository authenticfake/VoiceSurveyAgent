from fastapi import APIRouter, FastAPI


def create_app(auth_router: APIRouter | None = None) -> FastAPI:
    """
    Create a FastAPI application instance.

    Routers are injected from composition roots (e.g., API service, workers)
    so that individual KIT runs can provide different wiring without altering
    shared modules.
    """
    app = FastAPI(title="voicesurveyagent API")
    if auth_router:
        app.include_router(auth_router)
    return app