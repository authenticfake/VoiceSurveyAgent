# REQ-019: Admin Configuration API - Execution Guide

## Overview

This document provides instructions for running and testing the Admin Configuration API implementation for REQ-019.

## Prerequisites

### Required Software

- Python 3.12+
- PostgreSQL 14+ (for integration tests)
- pip (Python package manager)

### Optional Software

- Docker (for containerized database)
- AWS CLI (for Secrets Manager integration testing)

## Environment Setup

### 1. Create Virtual Environment

```bash
cd runs/kit/REQ-019
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file or export environment variables:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
export APP_ENV="test"
export PYTHONPATH="runs/kit/REQ-019/src"
export AWS_REGION="eu-central-1"
export AWS_SECRETS_MANAGER_PREFIX="voicesurvey-test"
```

### 4. Database Setup

#### Option A: Local PostgreSQL

```bash
# Create test database
createdb voicesurvey_test

# Run migrations (requires base migrations from REQ-001)
psql voicesurvey_test -f runs/kit/REQ-001/src/storage/sql/V0001.up.sql
psql voicesurvey_test -f runs/kit/REQ-019/src/storage/sql/V0003.up.sql

# Run seed data
psql voicesurvey_test -f runs/kit/REQ-019/src/storage/seed/seed.sql
```

#### Option B: Docker PostgreSQL

```bash
docker run -d \
  --name voicesurvey-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey_test \
  -p 5432:5432 \
  postgres:14
```

## Running Tests

### All Tests

```bash
cd runs/kit/REQ-019
PYTHONPATH=src pytest test/ -v
```

### Specific Test Files

```bash
# API tests
PYTHONPATH=src pytest test/test_admin_api.py -v

# Service tests
PYTHONPATH=src pytest test/test_admin_service.py -v

# Secrets Manager tests
PYTHONPATH=src pytest test/test_secrets_manager.py -v

# Migration tests
PYTHONPATH=src pytest test/test_migration_sql.py -v
```

### With Coverage

```bash
PYTHONPATH=src pytest test/ -v --cov=src --cov-report=html --cov-report=term
```

## Running the Application

### Development Server

```bash
cd runs/kit/REQ-019
PYTHONPATH=src uvicorn app.main:app --reload --port 8000
```

Note: You'll need to create a minimal `app/main.py` that includes the admin router:

```python
from fastapi import FastAPI
from app.admin.router import router as admin_router

app = FastAPI(title="VoiceSurveyAgent Admin API")
app.include_router(admin_router)
```

### API Documentation

Once running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Linting and Type Checking

### Lint with Ruff

```bash
cd runs/kit/REQ-019
ruff check src/ test/
```

### Type Check with MyPy

```bash
cd runs/kit/REQ-019
mypy src/ --ignore-missing-imports
```

### Security Scan with Bandit

```bash
cd runs/kit/REQ-019
bandit -r src/ -ll
```

## CI/CD Integration

### GitHub Actions

The LTC.json file defines the test contract. In CI:

```yaml
- name: Run REQ-019 Tests
  run: |
    cd runs/kit/REQ-019
    pip install -r requirements.txt
    PYTHONPATH=src pytest test/ -v --junitxml=reports/junit.xml
```

### Jenkins

```groovy
stage('REQ-019 Tests') {
    steps {
        dir('runs/kit/REQ-019') {
            sh 'pip install -r requirements.txt'
            sh 'PYTHONPATH=src pytest test/ -v --junitxml=reports/junit.xml'
        }
    }
}
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`:

1. Ensure PYTHONPATH includes the src directory:
   ```bash
   export PYTHONPATH=runs/kit/REQ-019/src
   ```

2. Or use editable install (if setup.py exists):
   ```bash
   pip install -e .
   ```

### Database Connection Issues

1. Verify PostgreSQL is running:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Check connection string format:
   ```
   postgresql://user:password@host:port/database
   ```

3. For async tests, ensure asyncpg is installed:
   ```bash
   pip install asyncpg
   ```

### AWS Secrets Manager Issues

For local development without AWS:
- Tests use `MockSecretsManager` automatically when `APP_ENV=test`
- No AWS credentials required for unit tests

For integration with real AWS:
1. Configure AWS credentials:
   ```bash
   aws configure
   ```
2. Ensure IAM permissions for Secrets Manager
3. Set `APP_ENV=development` or `APP_ENV=production`

## API Testing with curl

### Get Configuration

```bash
curl -X GET http://localhost:8000/api/admin/config \
  -H "X-User-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-User-Role: admin"
```

### Update Configuration

```bash
curl -X PUT http://localhost:8000/api/admin/config \
  -H "X-User-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-User-Role: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "telephony": {
      "max_concurrent_calls": 20
    }
  }'
```

### Get Audit Logs

```bash
curl -X GET "http://localhost:8000/api/admin/audit-logs?page=1&page_size=10" \
  -H "X-User-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-User-Role: admin"
```

## Artifacts

After running tests, find:
- JUnit report: `runs/kit/REQ-019/reports/junit.xml`
- Coverage report: `runs/kit/REQ-019/reports/coverage.xml`
- HTML coverage: `runs/kit/REQ-019/htmlcov/index.html`