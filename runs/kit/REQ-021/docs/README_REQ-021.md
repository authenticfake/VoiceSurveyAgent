# REQ-021: Observability Instrumentation

## Quick Start

```python
from fastapi import FastAPI
from infra.observability import setup_observability, get_logger

app = FastAPI()
setup_observability(app)

logger = get_logger(__name__)

@app.get("/api/example")
async def example():
    logger.info("Request received", user_id="123")
    return {"status": "ok"}
```

## Features

- ✅ Structured JSON logging
- ✅ Correlation ID propagation
- ✅ Prometheus metrics at `/metrics`
- ✅ Distributed tracing
- ✅ Health check endpoints

## Endpoints

| Path | Description |
|------|-------------|
| `/metrics` | Prometheus metrics |
| `/health` | Health check |
| `/ready` | Readiness probe |
| `/live` | Liveness probe |

## Environment Variables

```bash
LOG_LEVEL=INFO
METRICS_ENABLED=true
TRACING_ENABLED=true
```

## Running Tests

```bash
export PYTHONPATH=runs/kit/REQ-021/src
pytest runs/kit/REQ-021/test -v
```

See [KIT_REQ-021.md](KIT_REQ-021.md) for full documentation.
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-021**: Observability instrumentation

### Rationale
REQ-021 is marked as `open` in the plan and depends only on REQ-001 (database schema), which is already `in_progress`. This REQ provides foundational observability infrastructure that will be used by all other application components.

### In Scope
- Structured JSON logging with correlation ID support
- Prometheus-compatible metrics registry and endpoint
- OpenTelemetry-style distributed tracing
- Health, readiness, and liveness endpoints
- FastAPI integration middleware
- Configuration via environment variables
- PII redaction in logs
- Comprehensive unit and integration tests

### Out of Scope
- Full OpenTelemetry SDK integration (simplified implementation provided)
- OTLP exporter implementation (structure prepared for future addition)
- Grafana/CloudWatch dashboard configurations
- Alert rule definitions

### How to Run Tests

```bash
# Set up environment
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-021/src"

# Install dependencies
pip install -r runs/kit/REQ-021/requirements.txt

# Run all tests
python -m pytest runs/kit/REQ-021/test -v --tb=short

# Run specific test files
python -m pytest runs/kit/REQ-021/test/test_logging.py -v
python -m pytest runs/kit/REQ-021/test/test_metrics.py -v
python -m pytest runs/kit/REQ-021/test/test_tracing.py -v
python -m pytest runs/kit/REQ-021/test/test_health.py -v
python -m pytest runs/kit/REQ-021/test/test_integration.py -v
```

### Prerequisites
- Python 3.12+
- pip for package installation
- Optional: ruff for linting, mypy for type checking

### Dependencies and Mocks
- **No external mocks required** - All components are self-contained
- Tests use Starlette's `TestClient` for HTTP testing
- `pytest-asyncio` for async test support
- No database or external service dependencies

### Product Owner Notes
- The tracing implementation is a simplified version compatible with OpenTelemetry concepts but does not require the full OpenTelemetry SDK
- Metrics are stored in-memory; for production, consider using `prometheus_client` library for more robust metric collection
- PII redaction covers phone numbers and emails; additional patterns can be added to `PII_PATTERNS` in `logging.py`
- The health check system is pluggable - register checks for database, Redis, etc. as those components are implemented

### RAG Citations
- Referenced `runs/kit/REQ-019/src/app/shared/__init__.py` for shared module patterns
- Referenced `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` for understanding existing schema structure
- Referenced `PLAN.md` for module namespace conventions (`infra.observability`)
- Referenced `TECH_CONSTRAINTS.yaml` for observability stack requirements (CloudWatch, Prometheus, OpenTelemetry)

```json
{
  "index": [
    {
      "req": "REQ-021",
      "src": [
        "runs/kit/REQ-021/src/infra/__init__.py",
        "runs/kit/REQ-021/src/infra/observability/__init__.py",
        "runs/kit/REQ-021/src/infra/observability/config.py",
        "runs/kit/REQ-021/src/infra/observability/correlation.py",
        "runs/kit/REQ-021/src/infra/observability/logging.py",
        "runs/kit/REQ-021/src/infra/observability/metrics.py",
        "runs/kit/REQ-021/src/infra/observability/tracing.py",
        "runs/kit/REQ-021/src/infra/observability/middleware.py",
        "runs/kit/REQ-021/src/infra/observability/health.py",
        "runs/kit/REQ-021/src/infra/observability/fastapi_integration.py"
      ],
      "tests": [
        "runs/kit/REQ-021/test/test_logging.py",
        "runs/kit/REQ-021/test/test_correlation.py",
        "runs/kit/REQ-021/test/test_metrics.py",
        "runs/kit/REQ-021/test/test_tracing.py",
        "runs/kit/REQ-021/test/test_health.py",
        "runs/kit/REQ-021/test/test_integration.py",
        "runs/kit/REQ-021/test/conftest.py"
      ]
    }
  ]
}