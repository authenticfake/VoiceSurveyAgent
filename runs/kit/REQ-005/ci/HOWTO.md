# REQ-005: Campaign Validation Service - Execution Guide

## Overview

This KIT implements the campaign validation service that validates campaign configuration before activation. It ensures campaigns meet all requirements (contacts, questions, retry policy, time windows) before transitioning to running status.

## Prerequisites

### Required Software
- Python 3.12+
- pip or poetry for dependency management
- PostgreSQL 15+ (for integration tests with real database)

### Environment Setup

1. **Create and activate virtual environment:**
bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

2. **Set PYTHONPATH:**
bash
export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src:$PYTHONPATH"

3. **Install dependencies:**
bash
pip install -r runs/kit/REQ-005/requirements.txt

## Running Tests

### Unit Tests Only
bash
pytest runs/kit/REQ-005/test/test_validation.py -v

### Integration Tests Only
bash
pytest runs/kit/REQ-005/test/test_router_validation.py -v

### All Tests with Coverage
bash
pytest runs/kit/REQ-005/test/ \
  --cov=runs/kit/REQ-005/src \
  --cov-report=term-missing \
  --cov-report=xml:runs/kit/REQ-005/reports/coverage.xml \
  --junitxml=runs/kit/REQ-005/reports/junit.xml \
  -v

### Type Checking
bash
mypy runs/kit/REQ-005/src/app/campaigns/validation.py --ignore-missing-imports

### Linting
bash
ruff check runs/kit/REQ-005/src runs/kit/REQ-005/test
ruff format runs/kit/REQ-005/src runs/kit/REQ-005/test --check

## CI/CD Integration

### GitHub Actions
The LTC.json file defines all test cases that should be run in CI. Use the following workflow snippet:

yaml
- name: Run REQ-005 Tests
  run: |
    export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
    pip install -r runs/kit/REQ-005/requirements.txt
    pytest runs/kit/REQ-005/test/ --cov --junitxml=reports/junit.xml

### Jenkins Pipeline
groovy
stage('REQ-005 Validation') {
    steps {
        sh '''
            export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
            pip install -r runs/kit/REQ-005/requirements.txt
            pytest runs/kit/REQ-005/test/ --junitxml=reports/junit.xml
        '''
    }
    post {
        always {
            junit 'reports/junit.xml'
        }
    }
}

## Artifacts

### Reports Location
- JUnit XML: `runs/kit/REQ-005/reports/junit.xml`
- Coverage XML: `runs/kit/REQ-005/reports/coverage.xml`

### Source Files
- Validation Service: `runs/kit/REQ-005/src/app/campaigns/validation.py`
- Updated Router: `runs/kit/REQ-005/src/app/campaigns/router.py`
- Updated Schemas: `runs/kit/REQ-005/src/app/campaigns/schemas.py`
- Repository: `runs/kit/REQ-005/src/app/campaigns/repository.py`
- Service: `runs/kit/REQ-005/src/app/campaigns/service.py`
- Exceptions: `runs/kit/REQ-005/src/app/shared/exceptions.py`

## Troubleshooting

### Import Errors
If you encounter import errors, ensure PYTHONPATH includes all dependent REQ paths:
bash
export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

### Database Connection Issues
For tests that require database access, set:
bash
export DATABASE_URL="postgresql://user:password@localhost:5432/voicesurvey_test"
export DISABLE_TESTCONTAINERS="1"  # If not using testcontainers

### Missing Dependencies
Install all dependencies from requirements.txt:
bash
pip install -r runs/kit/REQ-005/requirements.txt

## API Endpoints Added

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/campaigns/{id}/validate` | Validate campaign for activation |
| POST | `/api/campaigns/{id}/activate` | Validate and activate campaign |
| POST | `/api/campaigns/{id}/pause` | Pause a running campaign |

## Validation Rules

The validation service checks:
1. Campaign must be in `draft` status
2. Campaign must have at least one contact
3. All 3 questions must be non-empty
4. `max_attempts` must be between 1 and 5
5. `allowed_call_start_local` must be before `allowed_call_end_local`