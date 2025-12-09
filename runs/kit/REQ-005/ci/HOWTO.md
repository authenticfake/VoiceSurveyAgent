# REQ-005: Campaign Validation Service - Execution Guide

## Overview

This KIT implements the campaign validation service that validates campaign configuration before activation. It ensures campaigns meet all requirements before transitioning from `draft` to `running` status.

## Prerequisites

### System Requirements
- Python 3.12+
- PostgreSQL 15+ (for integration tests)
- pip or poetry for dependency management

### Dependencies
The validation service depends on:
- REQ-001: Database schema (Campaign, Contact models)
- REQ-002: Authentication (CurrentUser)
- REQ-003: RBAC (require_campaign_manager)
- REQ-004: Campaign CRUD (CampaignRepository, Campaign model)

## Environment Setup

### 1. Set PYTHONPATH

The validation service imports from multiple REQ modules. Set PYTHONPATH to include all dependencies:

```bash
export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src:$PYTHONPATH"
```

### 2. Install Dependencies

```bash
# Install test dependencies
pip install -r runs/kit/REQ-005/requirements.txt

# Or with poetry (if using project-wide pyproject.toml)
poetry install
```

### 3. Database Configuration (for integration tests)

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/voicesurvey"
```

## Running Tests

### Unit Tests Only

```bash
# Run validation service unit tests
pytest runs/kit/REQ-005/test/test_validation_service.py -v

# With detailed output
pytest runs/kit/REQ-005/test/test_validation_service.py -v --tb=long
```

### API Integration Tests

```bash
# Run activation API tests
pytest runs/kit/REQ-005/test/test_activation_api.py -v
```

### All Tests with Coverage

```bash
# Run all tests with coverage report
pytest runs/kit/REQ-005/test/ -v \
  --cov=runs/kit/REQ-005/src \
  --cov-report=term-missing \
  --cov-report=xml:runs/kit/REQ-005/reports/coverage.xml \
  --junitxml=runs/kit/REQ-005/reports/junit.xml
```

### Quick Smoke Test

```bash
# Fast validation that tests pass
pytest runs/kit/REQ-005/test/ -q --tb=short
```

## Code Quality Checks

### Type Checking

```bash
mypy runs/kit/REQ-005/src --ignore-missing-imports
```

### Linting

```bash
ruff check runs/kit/REQ-005/src runs/kit/REQ-005/test
ruff format --check runs/kit/REQ-005/src runs/kit/REQ-005/test
```

### Security Scan

```bash
bandit -r runs/kit/REQ-005/src -ll
```

## API Usage

### Activate Campaign Endpoint

```bash
# POST /api/campaigns/{campaign_id}/activate
curl -X POST "http://localhost:8000/api/campaigns/{campaign_id}/activate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

### Expected Responses

**Success (200):**
```json
{
  "id": "uuid",
  "name": "Campaign Name",
  "status": "running",
  ...
}
```

**Validation Failed (400):**
```json
{
  "detail": {
    "code": "VALIDATION_FAILED",
    "message": "Campaign validation failed",
    "errors": [
      {"field": "contacts", "message": "Campaign must have at least one contact"},
      {"field": "max_attempts", "message": "Maximum attempts cannot exceed 5"}
    ]
  }
}
```

**Not Found (404):**
```json
{
  "detail": {
    "code": "CAMPAIGN_NOT_FOUND",
    "message": "Campaign not found"
  }
}
```

## Validation Rules

The service validates:

1. **Contacts**: Campaign must have at least one contact
2. **Questions**: All 3 questions must be non-empty
3. **Retry Policy**: max_attempts must be between 1 and 5
4. **Time Window**: allowed_call_start_local must be before allowed_call_end_local

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`, ensure PYTHONPATH includes all dependency paths:

```bash
echo $PYTHONPATH
# Should include: runs/kit/REQ-005/src:runs/kit/REQ-004/src:...
```

### Database Connection Issues

For tests that require database:
1. Ensure PostgreSQL is running
2. Verify DATABASE_URL is set correctly
3. Run migrations from REQ-001 first

### Test Isolation

Tests use mocks for database operations. If you need real database tests:
1. Set up test database
2. Run REQ-001 migrations
3. Use pytest fixtures for database session

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run REQ-005 Tests
  env:
    PYTHONPATH: runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src
  run: |
    pip install -r runs/kit/REQ-005/requirements.txt
    pytest runs/kit/REQ-005/test/ -v --cov --junitxml=reports/junit.xml
```

### Jenkins

```groovy
stage('REQ-005 Tests') {
    environment {
        PYTHONPATH = 'runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src'
    }
    steps {
        sh 'pip install -r runs/kit/REQ-005/requirements.txt'
        sh 'pytest runs/kit/REQ-005/test/ -v --junitxml=test-results.xml'
    }
}
```

## Artifacts

After running tests, find reports at:
- `runs/kit/REQ-005/reports/junit.xml` - Test results
- `runs/kit/REQ-005/reports/coverage.xml` - Coverage report