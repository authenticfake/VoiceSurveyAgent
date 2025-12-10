# KIT Documentation — REQ-021: Observability Instrumentation

## Summary

REQ-021 implements comprehensive observability instrumentation for the VoiceSurveyAgent application, providing:

1. **Structured JSON Logging** - All log entries in JSON format with correlation ID propagation
2. **Prometheus Metrics** - Application metrics exposed at `/metrics` endpoint
3. **Distributed Tracing** - OpenTelemetry-compatible tracing for request flows
4. **Health Checks** - Kubernetes-compatible health, readiness, and liveness endpoints

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| All log entries in structured JSON format | ✅ | `StructuredJsonFormatter` in `logging.py` |
| Correlation ID propagated across HTTP, telephony, LLM calls | ✅ | `CorrelationIdMiddleware` and `correlation_id_context` |
| Prometheus metrics endpoint at /metrics | ✅ | `metrics_endpoint` function and `MetricsRegistry` |
| OpenTelemetry traces for API requests | ✅ | `TracingMiddleware` and `Tracer` class |
| Log level configurable via environment variable | ✅ | `LOG_LEVEL` environment variable in `config.py` |

## Architecture

### Module Structure

```
infra/observability/
├── __init__.py          # Public API exports
├── config.py            # Configuration management
├── correlation.py       # Correlation ID handling
├── logging.py           # Structured JSON logging
├── metrics.py           # Prometheus metrics
├── tracing.py           # Distributed tracing
├── health.py            # Health check endpoints
├── middleware.py        # Combined observability middleware
└── fastapi_integration.py  # FastAPI setup helpers
```

### Key Components

#### 1. Logging (`logging.py`)

- `StructuredJsonFormatter`: Formats log records as JSON
- `StructuredLogger`: Wrapper with context support
- `get_logger(name)`: Factory function for loggers
- `configure_logging()`: Global logging configuration

Features:
- Automatic PII redaction (phone numbers, emails)
- Correlation ID inclusion
- Exception traceback formatting
- Contextual logging with bound fields

#### 2. Correlation (`correlation.py`)

- `CorrelationIdMiddleware`: Extracts/generates correlation IDs
- `get_correlation_id()`: Get current correlation ID
- `correlation_id_context()`: Context manager for correlation scope
- `inject_correlation_headers()`: Add correlation ID to outgoing requests

#### 3. Metrics (`metrics.py`)

- `Counter`: Monotonically increasing counter
- `Gauge`: Value that can go up and down
- `Histogram`: Distribution of values with buckets
- `MetricsRegistry`: Central registry for all metrics

Pre-defined metrics:
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram
- `call_attempts_total` - Call attempts by campaign and outcome
- `survey_completions_total` - Completed surveys
- `provider_errors_total` - Provider errors by type
- `llm_latency_seconds` - LLM request latency

#### 4. Tracing (`tracing.py`)

- `Span`: Represents a trace span
- `Tracer`: Creates and manages spans
- `TracingMiddleware`: Creates spans for HTTP requests
- `@traced`: Decorator for tracing functions

Features:
- Automatic parent-child span relationships
- Correlation ID as trace ID
- Configurable sampling rate
- Error status propagation

#### 5. Health (`health.py`)

- `HealthChecker`: Pluggable health check system
- `health_endpoint`: Returns overall health status
- `readiness_endpoint`: Kubernetes readiness probe
- `liveness_endpoint`: Kubernetes liveness probe

## Configuration

All configuration via environment variables:

```bash
# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT_JSON=true              # JSON or plain text
LOG_INCLUDE_TIMESTAMP=true
LOG_INCLUDE_CALLER=true
LOG_REDACT_PII=true

# Metrics
METRICS_ENABLED=true
METRICS_ENDPOINT=/metrics
METRICS_NAMESPACE=voicesurveyagent

# Tracing
TRACING_ENABLED=true
TRACING_SERVICE_NAME=voicesurveyagent
TRACING_SAMPLE_RATE=1.0
OTLP_ENDPOINT=                    # Optional OTLP collector
```

## Usage Examples

### Quick Setup

```python
from fastapi import FastAPI
from infra.observability import setup_observability

app = FastAPI()
setup_observability(app)
```

### Logging with Context

```python
from infra.observability import get_logger

logger = get_logger(__name__)

# Simple logging
logger.info("Processing request")

# With extra context
logger.info("Campaign activated", campaign_id="camp-123", contacts=500)

# With bound context
ctx_logger = logger.with_context(campaign_id="camp-123")
ctx_logger.info("Step 1 complete")
ctx_logger.info("Step 2 complete")
```

### Recording Metrics

```python
from infra.observability import get_metrics_registry

registry = get_metrics_registry()

# Counter
registry.call_attempts_total.inc(campaign_id="camp-123", outcome="completed")

# Histogram with timer
with registry.llm_latency_seconds.labels(provider="openai", model="gpt-4").time():
    response = await llm.complete(prompt)

# Gauge
registry.active_calls.set(current_active_count)
```

### Tracing

```python
from infra.observability import trace_span, traced

# Context manager
async def process_call(call_id: str):
    with trace_span("process_call", {"call_id": call_id}) as span:
        span.add_event("consent_received")
        # ... process call ...
        span.set_attribute("questions_answered", 3)

# Decorator
@traced(name="fetch_campaign")
async def fetch_campaign(campaign_id: str):
    return await db.get_campaign(campaign_id)
```

## Testing

```bash
# Run all tests
pytest runs/kit/REQ-021/test -v

# Run with coverage
pytest runs/kit/REQ-021/test --cov=runs/kit/REQ-021/src
```

## Dependencies

- `fastapi>=0.109.0` - Web framework
- `starlette>=0.35.0` - ASGI toolkit
- `pytest>=8.0.0` - Testing framework
- `pytest-asyncio>=0.23.0` - Async test support

## Integration Points

This module integrates with:
- **REQ-002**: Auth middleware uses correlation IDs
- **REQ-009**: Telephony adapter records provider metrics
- **REQ-011**: LLM gateway records latency metrics
- **REQ-015**: Event publisher includes correlation IDs
- **REQ-017**: Dashboard stats use metrics data