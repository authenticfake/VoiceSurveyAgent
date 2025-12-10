# REQ-021: Observability Instrumentation - Execution Guide

## Overview

This KIT implements observability instrumentation for the VoiceSurveyAgent application:
- Structured JSON logging with correlation ID propagation
- Prometheus-compatible metrics endpoint at `/metrics`
- OpenTelemetry-style distributed tracing
- Health check endpoints (`/health`, `/ready`, `/live`)

## Prerequisites

### Required Tools
- Python 3.12+
- pip (Python package manager)

### Optional Tools
- ruff (for linting)
- mypy (for type checking)
- pytest-cov (for coverage reports)

## Environment Setup

### 1. Create Virtual Environment (Recommended)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
pip install -r runs/kit/REQ-021/requirements.txt
```

### 3. Set PYTHONPATH

```bash
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-021/src"
```

### 4. Environment Variables

The observability system is configured via environment variables:

```bash
# Logging
export LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR, CRITICAL
export LOG_FORMAT_JSON=true        # true for JSON, false for plain text
export LOG_INCLUDE_TIMESTAMP=true
export LOG_INCLUDE_CALLER=true
export LOG_REDACT_PII=true

# Metrics
export METRICS_ENABLED=true
export METRICS_ENDPOINT=/metrics
export METRICS_NAMESPACE=voicesurveyagent

# Tracing
export TRACING_ENABLED=true
export TRACING_SERVICE_NAME=voicesurveyagent
export TRACING_SAMPLE_RATE=1.0     # 0.0 to 1.0
export OTLP_ENDPOINT=              # Optional OTLP collector endpoint
```

## Running Tests

### Run All Tests

```bash
python -m pytest runs/kit/REQ-021/test -v
```

### Run with Coverage

```bash
python -m pytest runs/kit/REQ-021/test -v --cov=runs/kit/REQ-021/src --cov-report=xml:reports/coverage-req021.xml
```

### Run Specific Test Files

```bash
# Logging tests
python -m pytest runs/kit/REQ-021/test/test_logging.py -v

# Metrics tests
python -m pytest runs/kit/REQ-021/test/test_metrics.py -v

# Tracing tests
python -m pytest runs/kit/REQ-021/test/test_tracing.py -v

# Health check tests
python -m pytest runs/kit/REQ-021/test/test_health.py -v

# Integration tests
python -m pytest runs/kit/REQ-021/test/test_integration.py -v
```

## Linting and Type Checking

### Lint with Ruff

```bash
pip install ruff
ruff check runs/kit/REQ-021/src
```

### Type Check with MyPy

```bash
pip install mypy
mypy runs/kit/REQ-021/src --ignore-missing-imports
```

## Usage in Application

### Basic Setup

```python
from fastapi import FastAPI
from infra.observability import setup_observability, get_logger

app = FastAPI()
setup_observability(app)

logger = get_logger(__name__)

@app.get("/api/example")
async def example():
    logger.info("Processing request", user_id="123")
    return {"status": "ok"}
```

### Using Correlation IDs

```python
from infra.observability import get_correlation_id, correlation_id_context

# Get current correlation ID (set by middleware)
cid = get_correlation_id()

# Create a new correlation context
with correlation_id_context("custom-id-123"):
    # All logs within this context will include this correlation ID
    logger.info("Processing with custom correlation")
```

### Recording Metrics

```python
from infra.observability import get_metrics_registry

registry = get_metrics_registry()

# Increment counter
registry.call_attempts_total.inc(campaign_id="camp-123", outcome="completed")

# Record histogram observation
registry.llm_latency_seconds.observe(0.5, provider="openai", model="gpt-4")

# Set gauge
registry.active_calls.set(10)
```

### Creating Trace Spans

```python
from infra.observability import trace_span, traced

# Using context manager
with trace_span("fetch_data", {"source": "database"}) as span:
    span.set_attribute("rows_fetched", 100)
    # ... do work ...

# Using decorator
@traced(name="process_campaign")
async def process_campaign(campaign_id: str):
    # ... do work ...
    pass
```

### Registering Health Checks

```python
from infra.observability.health import get_health_checker, HealthCheckResult, HealthStatus

async def check_database():
    # Check database connection
    is_connected = await db.ping()
    return HealthCheckResult(
        name="database",
        status=HealthStatus.HEALTHY if is_connected else HealthStatus.UNHEALTHY,
        message="Database connection OK" if is_connected else "Database connection failed"
    )

checker = get_health_checker()
checker.register("database", check_database)
```

## Endpoints

After setup, the following endpoints are available:

| Endpoint | Purpose |
|----------|---------|
| `/metrics` | Prometheus metrics in text format |
| `/health` | Health check (returns 200 if healthy, 503 if unhealthy) |
| `/ready` | Readiness check for Kubernetes |
| `/live` | Liveness check for Kubernetes |

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'infra'`:

```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-021/src"
```

### Tests Failing with Missing Dependencies

```bash
# Install all test dependencies
pip install pytest pytest-asyncio httpx
```

### Metrics Not Appearing

1. Ensure `METRICS_ENABLED=true`
2. Check that the `/metrics` endpoint is accessible
3. Verify metrics are being recorded (counters start at 0)

### Logs Not in JSON Format

1. Ensure `LOG_FORMAT_JSON=true`
2. Call `configure_logging()` at application startup
3. Check that you're using `get_logger()` from the observability module

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run REQ-021 Tests
  env:
    PYTHONPATH: runs/kit/REQ-021/src
    LOG_LEVEL: DEBUG
  run: |
    pip install -r runs/kit/REQ-021/requirements.txt
    pytest runs/kit/REQ-021/test -v --junitxml=reports/junit-req021.xml
```

### Jenkins Pipeline Example

```groovy
stage('REQ-021 Tests') {
    environment {
        PYTHONPATH = "runs/kit/REQ-021/src"
    }
    steps {
        sh 'pip install -r runs/kit/REQ-021/requirements.txt'
        sh 'pytest runs/kit/REQ-021/test -v'
    }
}
```

## Artifacts

| Path | Description |
|------|-------------|
| `runs/kit/REQ-021/src/infra/observability/` | Source code |
| `runs/kit/REQ-021/test/` | Test files |
| `reports/junit-req021.xml` | JUnit test report |
| `reports/coverage-req021.xml` | Coverage report |