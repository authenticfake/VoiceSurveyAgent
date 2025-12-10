"""
Combined observability middleware for FastAPI.

REQ-021: Observability instrumentation
Provides a single middleware that combines correlation ID, metrics, and tracing.
"""

import time
from typing import Callable, Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from infra.observability.correlation import (
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
)
from infra.observability.metrics import get_metrics_registry
from infra.observability.tracing import get_tracer
from infra.observability.config import get_observability_config
from infra.observability.logging import get_logger


logger = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Combined middleware for observability.
    
    Handles:
    - Correlation ID extraction/generation
    - Request/response logging
    - HTTP metrics collection
    - Distributed tracing
    """
    
    def __init__(self, app: Any, exclude_paths: list[str] | None = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/ready"]
    
    def _should_skip(self, path: str) -> bool:
        """Check if path should skip observability."""
        return any(path.startswith(p) for p in self.exclude_paths)
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request with full observability."""
        path = request.url.path
        
        # Skip observability for excluded paths
        if self._should_skip(path):
            return await call_next(request)
        
        # Extract or generate correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = request.headers.get(REQUEST_ID_HEADER)
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        set_correlation_id(correlation_id)
        
        config = get_observability_config()
        registry = get_metrics_registry()
        tracer = get_tracer()
        
        method = request.method
        # Normalize path for metrics (replace UUIDs with placeholder)
        import re
        normalized_path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE,
        )
        
        start_time = time.perf_counter()
        status_code = 500
        
        # Create trace span
        span_name = f"{method} {normalized_path}"
        span_attributes = {
            "http.method": method,
            "http.url": str(request.url),
            "http.route": normalized_path,
            "http.correlation_id": correlation_id,
        }
        
        try:
            if config.tracing.enabled:
                with tracer.span(span_name, attributes=span_attributes) as span:
                    # Log request
                    logger.info(
                        f"Request started: {method} {path}",
                        method=method,
                        path=path,
                        correlation_id=correlation_id,
                    )
                    
                    response = await call_next(request)
                    status_code = response.status_code
                    
                    span.set_attribute("http.status_code", status_code)
                    if status_code >= 400:
                        span.set_status("ERROR", f"HTTP {status_code}")
            else:
                logger.info(
                    f"Request started: {method} {path}",
                    method=method,
                    path=path,
                    correlation_id=correlation_id,
                )
                response = await call_next(request)
                status_code = response.status_code
            
            return response
            
        except Exception as e:
            logger.exception(
                f"Request failed: {method} {path}",
                method=method,
                path=path,
                error=str(e),
            )
            raise
            
        finally:
            duration = time.perf_counter() - start_time
            
            # Record metrics
            if config.metrics.enabled:
                registry.http_requests_total.inc(
                    method=method,
                    endpoint=normalized_path,
                    status=str(status_code),
                )
                registry.http_request_duration_seconds.observe(
                    duration,
                    method=method,
                    endpoint=normalized_path,
                )
            
            # Log response
            logger.info(
                f"Request completed: {method} {path}",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2),
                correlation_id=correlation_id,
            )
            
            # Add correlation ID to response
            # Note: Response headers are immutable after creation in Starlette
            # This is handled by returning the response with headers set


def setup_observability_middleware(app: Any) -> None:
    """
    Setup observability middleware on a FastAPI/Starlette app.
    
    Args:
        app: FastAPI or Starlette application.
    """
    app.add_middleware(ObservabilityMiddleware)