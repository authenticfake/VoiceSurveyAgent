# HOWTO — REQ-003: RBAC Authorization Middleware

## Prerequisites

- Python 3.12+
- PostgreSQL 15+ (for integration tests)
- pip or poetry for dependency management

## Environment Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov httpx pyjwt[crypto] structlog sqlalchemy[asyncio] asyncpg fastapi pydantic pydantic-settings
```

### 3. Set Environment Variables

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
export OIDC_ISSUER_URL="https://idp.example.com"
export OIDC_CLIENT_ID="test-client-id"
export OIDC_CLIENT_SECRET="test-secret"
export OIDC_ROLE_CLAIM="role"
export JWT_SECRET_KEY="test-secret-key-for-testing-only"
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-004/src"
```

### 4. Set PYTHONPATH

```bash
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-004/src:$PYTHONPATH"
```

## Running Tests

### All Tests

```bash
pytest runs/kit/REQ-003/test/ -v
```

### With Coverage

```bash
pytest runs/kit/REQ-003/test/ -v --cov=app.auth --cov-report=term-missing
```

### Specific Test File

```bash
pytest runs/kit/REQ-003/test/test_rbac.py -v
pytest runs/kit/REQ-003/test/test_auth_service.py -v
```

## Linting and Type Checking

```bash
# Lint
ruff check runs/kit/REQ-003/src

# Type check
mypy runs/kit/REQ-003/src --ignore-missing-imports

# Security scan
bandit -r runs/kit/REQ-003/src -ll
```

## Container Execution

```bash
docker run --rm \
  -v $(pwd):/app \
  -w /app \
  -e DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:5432/voicesurvey_test" \
  -e OIDC_ISSUER_URL="https://idp.example.com" \
  -e OIDC_CLIENT_ID="test-client-id" \
  -e PYTHONPATH="/app/runs/kit/REQ-003/src:/app/runs/kit/REQ-004/src" \
  python:3.12-slim \
  bash -c "pip install pytest pytest-asyncio httpx pyjwt structlog sqlalchemy asyncpg fastapi pydantic pydantic-settings && pytest runs/kit/REQ-003/test/ -v"
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

1. Ensure PYTHONPATH includes both REQ-003 and REQ-004 src directories
2. Check that you're running from the project root

### Database Connection Errors

For tests that don't require a real database, mocks are used. If you see connection errors:

1. Verify DATABASE_URL is set correctly
2. Ensure PostgreSQL is running
3. Create the test database if needed

### JWT Validation Errors

Tests mock the JWKS client. For real token validation:

1. Ensure OIDC_ISSUER_URL points to a valid IdP
2. Verify the IdP's JWKS endpoint is accessible

## Artifacts

After running tests with coverage:

- `reports/junit.xml` - JUnit test results
- `reports/coverage.xml` - Coverage report in Cobertura format
- `.coverage` - Coverage data file