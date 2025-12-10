"""
FastAPI integration for observability.

REQ-021: Observability instrumentation
Provides easy setup for FastAPI applications.
"""

from typing import Optional, List

from fastapi import FastAPI
from starlette.routing import Route

from infra.observability.config import ObservabilityConfig, get_observability_config
from infra.observability.logging import configure_logging, get_logger
from infra.observability.tracing import configure_tracing
from infra.observability.metrics import metrics_endpoint
from infra.observability.health import (
    health_endpoint,
    readiness_endpoint,
    liveness_endpoint,
)
from infra.observability.middleware import ObservabilityMiddleware


logger = get_logger(__name__)


def setup_observability(
    app: FastAPI,
    config: Optional[ObservabilityConfig] = None,
    exclude_paths: Optional[List[str]] = None,
) -> None:
    """
    Setup complete observability for a FastAPI application.
    
    This function:
    - Configures structured JSON logging
    - Adds correlation ID middleware
    - Adds metrics collection middleware
    - Adds distributed tracing middleware
    - Registers /metrics, /health, /ready, /live endpoints
    
    Args:
        app: FastAPI application instance.
        config: Optional observability configuration.
        exclude_paths: Paths to exclude from observability middleware.
    """
    config = config or get_observability_config()
    
    # Configure logging
    configure_logging(
        level=config.logging.level,
        format_json=config.logging.format_json,
    )
    
    # Configure tracing
    if config.tracing.enabled:
        configure_tracing(
            service_name=config.tracing.service_name,
            sample_rate=config.tracing.sample_rate,
        )
    
    # Add observability middleware
    default_exclude = ["/health", "/ready", "/live", "/metrics", "/docs", "/openapi.json"]
    exclude = list(set(default_exclude + (exclude_paths or [])))
    app.add_middleware(ObservabilityMiddleware, exclude_paths=exclude)
    
    # Register observability endpoints
    if config.metrics.enabled:
        app.add_route(
            config.metrics.endpoint_path,
            metrics_endpoint,
            methods=["GET"],
            name="metrics",
        )
    
    # Health endpoints
    app.add_route("/health", health_endpoint, methods=["GET"], name="health")
    app.add_route("/ready", readiness_endpoint, methods=["GET"], name="readiness")
    app.add_route("/live", liveness_endpoint, methods=["GET"], name="liveness")
    
    logger.info(
        "Observability configured",
        logging_level=config.logging.level.value,
        metrics_enabled=config.metrics.enabled,
        tracing_enabled=config.tracing.enabled,
        tracing_sample_rate=config.tracing.sample_rate,
    )


def create_observable_app(
    title: str = "VoiceSurveyAgent",
    version: str = "0.1.0",
    config: Optional[ObservabilityConfig] = None,
    **kwargs,
) -> FastAPI:
    """
    Create a FastAPI application with observability pre-configured.
    
    Args:
        title: Application title.
        version: Application version.
        config: Optional observability configuration.
        **kwargs: Additional FastAPI constructor arguments.
        
    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(title=title, version=version, **kwargs)
    setup_observability(app, config=config)
    return app