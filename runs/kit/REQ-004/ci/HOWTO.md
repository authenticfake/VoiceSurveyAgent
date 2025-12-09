# REQ-004: Campaign CRUD API - Execution Guide

## Overview

This document provides instructions for running and testing the Campaign CRUD API implementation for REQ-004.

## Prerequisites

### Required Software
- Python 3.12+
- PostgreSQL 15+ (for integration tests with real database)
- pip or Poetry for dependency management

### Environment Variables

Create a `.env` file or export the following environment variables:

```bash
# Database
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/voicesurvey_test"

# OIDC Configuration (for auth middleware)
export OIDC_ISSUER_URL="https://test.auth0.com/"
export OIDC_CLIENT_ID="test-client-id"
export OIDC_CLIENT_SECRET="test-client-secret"

# JWT Configuration
export JWT_SECRET_KEY="test-secret-key-for-jwt-signing-min-32-chars"
export JWT_ALGORITHM="HS256"
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES="30"

# Logging
export LOG_LEVEL="DEBUG"
```

## Installation

### Option 1: Using pip directly

```bash
# Navigate to project root
cd /path/to/project

# Install dependencies
pip install -r runs/kit/REQ-004/requirements.txt

# Also install dependencies from dependent REQs
pip install -r runs/kit/REQ-002/requirements.txt
pip install -r runs/kit/REQ-003/requirements.txt
```

### Option 2: Using virtual environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r runs/kit/REQ-004/requirements.txt
```

## Running Tests

### Setting PYTHONPATH

The tests require access to modules from REQ-002, REQ-003, and REQ-004. Set PYTHONPATH accordingly:

```bash
export PYTHONPATH=runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src
```

### Run All Tests

```bash
pytest runs/kit/REQ-004/test -v
```

### Run Unit Tests Only

```bash
pytest runs/kit/REQ-004/test/test_campaigns_unit.py -v
```

### Run API Tests Only

```bash
pytest runs/kit/REQ-004/test/test_campaigns_api.py -v
```

### Run Tests with Coverage

```bash
pytest runs/kit/REQ-004/test -v \
  --cov=app.campaigns \
  --cov-report=term-missing \
  --cov-report=xml:reports/coverage.xml \
  --junitxml=reports/junit.xml
```

## Code Quality Checks

### Linting with Ruff

```bash
ruff check runs/kit/REQ-004/src
```

### Type Checking with MyPy

```bash
mypy runs/kit/REQ-004/src --ignore-missing-imports
```

### Security Scan with Bandit

```bash
bandit -r runs/kit/REQ-004/src -ll
```

## API Endpoints

The Campaign CRUD API provides the following endpoints:

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| POST | `/api/campaigns` | Create new campaign | campaign_manager, admin |
| GET | `/api/campaigns` | List campaigns (paginated) | viewer, campaign_manager, admin |
| GET | `/api/campaigns/{id}` | Get campaign details | viewer, campaign_manager, admin |
| PUT | `/api/campaigns/{id}` | Update campaign | campaign_manager, admin |
| DELETE | `/api/campaigns/{id}` | Delete campaign (soft) | campaign_manager, admin |
| POST | `/api/campaigns/{id}/status` | Transition status | campaign_manager, admin |

## Testing with curl

### Create Campaign

```bash
curl -X POST http://localhost:8000/api/campaigns \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "Test Campaign",
    "description": "Test description",
    "language": "en",
    "intro_script": "Hello, this is a test survey...",
    "question_1_text": "How satisfied are you?",
    "question_1_type": "scale",
    "question_2_text": "What could we improve?",
    "question_2_type": "free_text",
    "question_3_text": "How likely to recommend?",
    "question_3_type": "numeric",
    "max_attempts": 3,
    "retry_interval_minutes": 60,
    "allowed_call_start_local": "09:00:00",
    "allowed_call_end_local": "18:00:00"
  }'
```

### List Campaigns

```bash
curl -X GET "http://localhost:8000/api/campaigns?status=draft&page=1&page_size=20" \
  -H "Authorization: Bearer <token>"
```

### Get Campaign

```bash
curl -X GET http://localhost:8000/api/campaigns/{campaign_id} \
  -H "Authorization: Bearer <token>"
```

### Update Campaign

```bash
curl -X PUT http://localhost:8000/api/campaigns/{campaign_id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "Updated Campaign Name",
    "description": "Updated description"
  }'
```

### Transition Status

```bash
curl -X POST http://localhost:8000/api/campaigns/{campaign_id}/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"status": "running"}'
```

### Delete Campaign

```bash
curl -X DELETE http://localhost:8000/api/campaigns/{campaign_id} \
  -H "Authorization: Bearer <token>"
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure PYTHONPATH includes all required source directories:

```bash
export PYTHONPATH=runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src
```

### Database Connection Issues

1. Ensure PostgreSQL is running
2. Verify DATABASE_URL is correctly set
3. Check that the database exists and user has permissions

### Authentication Errors

1. Verify OIDC configuration is correct
2. Ensure JWT_SECRET_KEY is at least 32 characters
3. Check token expiration settings

## CI/CD Integration

### GitHub Actions

The LTC.json file defines test cases that can be executed in CI:

```yaml
- name: Run REQ-004 Tests
  run: |
    pip install -r runs/kit/REQ-004/requirements.txt
    export PYTHONPATH=runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src
    pytest runs/kit/REQ-004/test -v --cov=app.campaigns
```

### Jenkins

```groovy
stage('REQ-004 Tests') {
    steps {
        sh 'pip install -r runs/kit/REQ-004/requirements.txt'
        sh 'PYTHONPATH=runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src pytest runs/kit/REQ-004/test -v'
    }
}
```

## Artifacts

After running tests with coverage, the following artifacts are generated:

- `reports/junit.xml` - JUnit test results
- `reports/coverage.xml` - Coverage report in Cobertura format