# REQ-005: Campaign Validation Service - Execution Guide

## Overview

This REQ implements the campaign validation service that checks if a campaign meets all requirements for activation:
- Campaign has at least one contact
- All three questions are non-empty
- Retry policy is valid (1-5 attempts)
- Time window is valid (start < end)
- Campaign is in draft status

## Prerequisites

### System Requirements
- Python 3.12+
- PostgreSQL 15+ (for integration tests)
- pip or poetry for dependency management

### Dependencies
Install from the requirements.txt:
bash
cd runs/kit/REQ-005
pip install -r requirements.txt

## Environment Setup

### Required Environment Variables
bash
export DATABASE_URL="postgresql://user:password@localhost:5432/voicesurvey_test"
export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

### Alternative: Using .env file
Create a `.env` file in the project root:

DATABASE_URL=postgresql://user:password@localhost:5432/voicesurvey_test

## Running Tests

### All Tests
bash
cd runs/kit/REQ-005
pytest test -v

### Specific Test Files
bash
# Validation service unit tests
pytest test/test_validation.py -v

# Service activation tests
pytest test/test_service_activation.py -v

# Router endpoint tests
pytest test/test_router_validation.py -v

### With Coverage
bash
pytest test --cov=src --cov-report=term-missing --cov-report=xml:reports/coverage.xml

## Code Quality Checks

### Linting
bash
ruff check src test

### Type Checking
bash
mypy src --ignore-missing-imports

### Security Scan
bash
bandit -r src -ll

## API Endpoints

### Validate Campaign
bash
GET /api/campaigns/{campaign_id}/validate

Returns validation result with any errors:
json
{
  "is_valid": false,
  "errors": [
    {"field": "contacts", "message": "Campaign must have at least one contact", "code": "NO_CONTACTS"}
  ]
}

### Activate Campaign
bash
POST /api/campaigns/{campaign_id}/activate

Validates and activates the campaign:
json
{
  "campaign_id": "uuid",
  "status": "running",
  "message": "Campaign activated successfully"
}

## Troubleshooting

### Import Errors
Ensure PYTHONPATH includes all dependent REQ source directories:
bash
export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

### Database Connection Issues
1. Verify PostgreSQL is running
2. Check DATABASE_URL format
3. Ensure database exists and user has permissions

### Test Failures
1. Run with verbose output: `pytest -v --tb=long`
2. Check for missing dependencies
3. Verify mock configurations match expected interfaces

## CI/CD Integration

### GitHub Actions
The LTC.json defines the test cases for CI:
- install_deps: Install Python dependencies
- lint: Run ruff linter
- types: Run mypy type checker
- tests: Run pytest suite

### Jenkins Pipeline
groovy
stage('REQ-005 Tests') {
    steps {
        sh 'cd runs/kit/REQ-005 && pip install -r requirements.txt'
        sh 'cd runs/kit/REQ-005 && pytest test -v --junitxml=reports/junit.xml'
    }
}