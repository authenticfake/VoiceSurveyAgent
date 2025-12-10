"""
Observability module providing logging, metrics, and tracing.

REQ-021: Observability instrumentation
- All log entries in structured JSON format
- Correlation ID propagated across HTTP, telephony, LLM calls
- Prometheus metrics endpoint at /metrics
- OpenTelemetry traces for API requests
- Log level configurable via environment variable
"""

from infra.observability.logging import (
    configure_logging,
    get_logger,
    StructuredLogger,
)
from infra.observability.correlation import (
    CorrelationIdMiddleware,
    get_correlation_id,
    set_correlation_id,
    correlation_id_context,
)
from infra.observability.metrics import (
    MetricsRegistry,
    get_metrics_registry,
    metrics_endpoint,
)
from infra.observability.tracing import (
    configure_tracing,
    get_tracer,
    trace_span,
    TracingMiddleware,
)

__all__ = [
    # Logging
    "configure_logging",
    "get_logger",
    "StructuredLogger",
    # Correlation
    "CorrelationIdMiddleware",
    "get_correlation_id",
    "set_correlation_id",
    "correlation_id_context",
    # Metrics
    "MetricsRegistry",
    "get_metrics_registry",
    "metrics_endpoint",
    # Tracing
    "configure_tracing",
    "get_tracer",
    "trace_span",
    "TracingMiddleware",
]