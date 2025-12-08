# REQ-004: Campaign CRUD API

## Summary

This module implements the Campaign CRUD API for the VoiceSurveyAgent system, providing REST endpoints for managing survey campaigns with proper state machine validation and role-based access control.

## Quick Start

bash
# Install dependencies
cd runs/kit/REQ-004
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey"
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run tests
pytest test/ -v

# Start development server
uvicorn app.main:app --reload

## Features

- **Campaign CRUD Operations**: Create, read, update, delete campaigns
- **State Machine**: Enforced status transitions (draft → scheduled → running → completed)
- **Field Validation**: Status-dependent field update restrictions
- **Pagination**: Configurable page size with status filtering
- **RBAC Integration**: Role-based access control for all endpoints

## API Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| POST | /api/campaigns | Create campaign | campaign_manager |
| GET | /api/campaigns | List campaigns | viewer |
| GET | /api/campaigns/{id} | Get campaign | viewer |
| PUT | /api/campaigns/{id} | Update campaign | campaign_manager |
| DELETE | /api/campaigns/{id} | Delete campaign | campaign_manager |
| POST | /api/campaigns/{id}/status | Change status | campaign_manager |

## Dependencies

- REQ-001: Database schema
- REQ-003: RBAC middleware

## Testing

bash
# Run all tests
pytest test/ -v

# Run with coverage
pytest test/ --cov=src/app --cov-report=term-missing

# Run specific test file
pytest test/test_campaign_crud.py -v

## Documentation

- [Full KIT Documentation](./KIT_REQ-004.md)
- [API Collection](../test/api/campaigns.json)
- [Execution Guide](../ci/HOWTO.md)

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-004**: Campaign CRUD API

### Rationale
REQ-004 is the next open REQ in the dependency chain. It depends on REQ-003 (RBAC authorization middleware) which is marked as in_progress. The implementation builds upon:
- REQ-001: Database schema (campaigns table, users table)
- REQ-002/REQ-003: Authentication and RBAC middleware

### In Scope
- Campaign CRUD endpoints (POST, GET, PUT, DELETE)
- Paginated campaign listing with status filter
- Campaign status transitions with state machine validation
- Field update restrictions based on campaign status
- RBAC enforcement (viewer, campaign_manager, admin roles)
- Soft delete functionality (status → cancelled)

### Out of Scope
- Campaign activation validation (REQ-005)
- Contact CSV upload (REQ-006)
- Call scheduling integration (REQ-008)

### How to Run Tests

bash
# Navigate to REQ-004 directory
cd runs/kit/REQ-004

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
export APP_ENV="dev"

# Ensure database has migrations applied
psql -d voicesurvey_test -f ../REQ-001/src/storage/sql/V0001.up.sql

# Run tests
pytest test/ -v --tb=short

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ with test database
- Migrations from REQ-001 applied
- Environment variables configured

### Dependencies and Mocks
- **Database**: Uses real PostgreSQL with transaction rollback for test isolation
- **Authentication**: JWT tokens created with test secret for development mode
- **RBAC**: Real middleware with role hierarchy enforcement
- **No external service mocks**: All tests use real database operations

### Product Owner Notes
- Campaign status transitions follow strict state machine rules
- Field update restrictions prevent modification of critical fields after campaign activation
- Soft delete preserves audit trail by setting status to cancelled
- Pagination defaults to 20 items per page, max 100

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql`: Used for understanding campaign table schema, enum types, and constraints
- `runs/kit/REQ-001/src/storage/seed/seed.sql`: Referenced for understanding data relationships and test data patterns
- `docs/harper/lane-guides/python.md`: Used for project structure, testing patterns, and FastAPI conventions

json
{
  "index": [
    {
      "req": "REQ-004",
      "src": [
        "runs/kit/REQ-004/src/app/__init__.py",
        "runs/kit/REQ-004/src/app/config.py",
        "runs/kit/REQ-004/src/app/main.py",
        "runs/kit/REQ-004/src/app/shared/__init__.py",
        "runs/kit/REQ-004/src/app/shared/database.py",
        "runs/kit/REQ-004/src/app/shared/exceptions.py",
        "runs/kit/REQ-004/src/app/shared/logging.py",
        "runs/kit/REQ-004/src/app/auth/__init__.py",
        "runs/kit/REQ-004/src/app/auth/schemas.py",
        "runs/kit/REQ-004/src/app/auth/middleware.py",
        "runs/kit/REQ-004/src/app/auth/rbac.py",
        "runs/kit/REQ-004/src/app/campaigns/__init__.py",
        "runs/kit/REQ-004/src/app/campaigns/models.py",
        "runs/kit/REQ-004/src/app/campaigns/schemas.py",
        "runs/kit/REQ-004/src/app/campaigns/repository.py",
        "runs/kit/REQ-004/src/app/campaigns/service.py",
        "runs/kit/REQ-004/src/app/campaigns/router.py"
      ],
      "tests": [
        "runs/kit/REQ-004/test/__init__.py",
        "runs/kit/REQ-004/test/conftest.py",
        "runs/kit/REQ-004/test/test_campaign_crud.py",
        "runs/kit/REQ-004/test/test_campaign_service.py"
      ]
    }
  ]
}