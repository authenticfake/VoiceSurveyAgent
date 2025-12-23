*** BEGIN FILE: src/app/main.py
"""
FastAPI application entry point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncio
import hashlib

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import text

from app.auth.router import router as auth_router
from app.campaigns.router import router as campaigns_router
from app.contacts.router import router as contacts_router  # <-- IMPORTANT
from app.config import get_settings
from app.shared.database import db_manager
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.logging import get_logger, setup_logging
from app.contacts.exclusions.router import router as exclusions_router
from app.telephony.webhooks.router import router as telephony_webhooks_router

from app.calls.scheduler import CallScheduler, CallSchedulerConfig
from app.telephony.config import get_telephony_config
from app.telephony.factory import get_telephony_provider

import app.email.models  # noqa: F401

logger = get_logger(__name__)


def _advisory_lock_id(key: str) -> int:
    """Derive a stable signed bigint lock id from an arbitrary string key."""
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    # Use 63-bit positive space to avoid signed bigint surprises.
    return int.from_bytes(digest, "big", signed=False) & 0x7FFF_FFFF_FFFF_FFFF


async def _scheduler_supervisor(app: FastAPI) -> None:
    """Run the scheduler loop only on the process that becomes DB lock leader.

    This makes the scheduler production-safe under `uvicorn --workers N` and multi-replica,
    without requiring Redis/Kubernetes.
    """
    settings = get_settings()
    telephony_cfg = get_telephony_config()

    lock_id = _advisory_lock_id(settings.scheduler_lock_key)
    retry_sleep = 5

    logger.info(
        "Scheduler supervisor starting",
        extra={
            "scheduler_enabled": settings.scheduler_enabled,
            "interval_seconds": settings.scheduler_interval_seconds,
            "lock_id": lock_id,
        },
    )

    while True:
        try:
            # Dedicated connection used to hold the advisory lock.
            async with db_manager.engine.connect() as conn:
                res = await conn.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": lock_id},
                )
                acquired = bool(res.scalar())

                if not acquired:
                    logger.info(
                        "Scheduler leader lock busy; standby",
                        extra={"lock_id": lock_id, "sleep_seconds": retry_sleep},
                    )
                    await asyncio.sleep(retry_sleep)
                    continue

                logger.info("Scheduler leader lock acquired", extra={"lock_id": lock_id})

                cfg = CallSchedulerConfig(
                    interval_seconds=settings.scheduler_interval_seconds,
                    max_concurrent_calls=telephony_cfg.max_concurrent_calls,
                )

                # Build provider once for this worker. (Factory already caches singleton unless force_new.)
                provider = get_telephony_provider()

                # Leader loop: run ticks until cancelled or connection breaks.
                while True:
                    try:
                        async with db_manager.session() as session:
                            scheduler = CallScheduler(
                                session=session,
                                telephony_provider=provider,
                                config=cfg,
                                callback_base_url=telephony_cfg.webhook_base_url,
                                outbound_number=telephony_cfg.twilio_from_number or "+10000000000",
                            )
                            await scheduler.run_once()
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logger.exception("Scheduler tick failed")

                    await asyncio.sleep(cfg.interval_seconds)

        except asyncio.CancelledError:
            logger.info("Scheduler supervisor cancelled; stopping")
            raise
        except Exception:
            logger.exception(
                "Scheduler supervisor error; retrying",
                extra={"sleep_seconds": retry_sleep},
            )
            await asyncio.sleep(retry_sleep)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    setup_logging()
    settings = get_settings()

    logger.info("Application starting", extra={"env": settings.app_env})

    scheduler_task: asyncio.Task[None] | None = None
    if settings.scheduler_enabled:
        scheduler_task = asyncio.create_task(_scheduler_supervisor(app))
        app.state.scheduler_task = scheduler_task
        logger.info("Scheduler enabled; background task created")

    yield

    logger.info("Shutting down application")

    scheduler_task = getattr(app.state, "scheduler_task", None)
    if scheduler_task is not None:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        logger.info("Scheduler background task stopped")

    await db_manager.close()
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

    # Map domain exceptions to HTTP responses
    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # Request validation (FastAPI/Pydantic) -> consistent 422 payload
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(
                {
                    "field": field,
                    "message": error["msg"],
                    "type": error["type"],
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "errors": errors,
                }
            },
        )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router)
    app.include_router(campaigns_router)
    app.include_router(contacts_router)
    app.include_router(exclusions_router)
    app.include_router(telephony_webhooks_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    return app


app = create_app()
*** END FILE