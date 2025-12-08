# REQ-004: Campaign CRUD API

## Summary
Implements RESTful API endpoints for managing survey campaigns, including creation, retrieval, updates, and soft deletion with proper state machine enforcement.

## Quick Start

```bash
# Install dependencies
pip install -r runs/kit/REQ-004/requirements.txt

# Set environment
export PYTHONPATH=runs/kit/REQ-001/src:runs/kit/REQ-002/src:runs/kit/REQ-003/src:runs/kit/REQ-004/src
export DATABASE_URL="sqlite+aiosqlite:///:memory:"

# Run tests
pytest runs/kit/REQ-004/test -v
```

## Features
- Campaign CRUD operations
- Paginated listing with status filter
- State machine for campaign lifecycle
- Field update validation based on status
- Soft delete (status → cancelled)

## API Reference
See `test/api/campaigns.json` for complete API documentation with example requests.

## Dependencies
- REQ-001: Database schema
- REQ-002: Authentication
- REQ-003: Authorization
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
**REQ-004: Campaign CRUD API**

### Rationale
REQ-004 depends on REQ-003 (RBAC authorization middleware) which is now complete. This REQ implements the core campaign management functionality that other REQs (REQ-005, REQ-006, etc.) will build upon.

### In Scope
- Campaign CRUD endpoints (POST, GET, PUT, DELETE)
- Campaign status update endpoint (PATCH)
- State machine for campaign lifecycle
- Pagination and filtering for list endpoint
- Field update validation based on campaign status
- Soft delete functionality

### Out of Scope
- Campaign validation for activation (REQ-005)
- Contact CSV upload (REQ-006)
- Campaign statistics and dashboard (REQ-017)

### How to Run Tests
```bash
# Set PYTHONPATH to include all dependent modules
export PYTHONPATH=runs/kit/REQ-001/src:runs/kit/REQ-002/src:runs/kit/REQ-003/src:runs/kit/REQ-004/src

# Run all tests
pytest runs/kit/REQ-004/test -v --cov=app.campaigns --cov-report=term-missing

# Run specific test files
pytest runs/kit/REQ-004/test/test_campaign_service.py -v
pytest runs/kit/REQ-004/test/test_campaign_router.py -v
```

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ (production) or SQLite (testing)
- REQ-001 migrations applied
- REQ-002 authentication configured
- REQ-003 RBAC middleware available

### Dependencies and Mocks
- **Database**: Uses SQLite in-memory for tests via `aiosqlite`
- **Authentication**: Mocked via FastAPI dependency overrides
- **Authorization**: Mocked via dependency overrides for `require_role`
- **Repository**: Mocked with `AsyncMock` for service tests

### Product Owner Notes
- State machine follows SPEC: draft→scheduled→running→paused→completed/cancelled
- Only draft and scheduled campaigns can have fields updated
- Soft delete sets status to cancelled rather than removing records
- All endpoints require authentication; modification endpoints require campaign_manager role

### RAG Citations
- `runs/kit/REQ-001/src/app/shared/models/campaign.py` - Campaign model structure
- `runs/kit/REQ-001/src/app/shared/models/enums.py` - CampaignStatus enum
- `runs/kit/REQ-002/src/app/auth/middleware.py` - Authentication middleware patterns
- `runs/kit/REQ-003/src/app/auth/rbac.py` - RBAC decorator patterns
- `docs/harper/lane-guides/python.md` - Python lane conventions

### Index
```json
{
  "index": [
    {
      "req": "REQ-004",
      "src": [
        "runs/kit/REQ-004/src/app/campaigns/__init__.py",
        "runs/kit/REQ-004/src/app/campaigns/schemas.py",
        "runs/kit/REQ-004/src/app/campaigns/repository.py",
        "runs/kit/REQ-004/src/app/campaigns/service.py",
        "runs/kit/REQ-004/src/app/campaigns/router.py"
      ],
      "tests": [
        "runs/kit/REQ-004/test/test_campaign_schemas.py",
        "runs/kit/REQ-004/test/test_campaign_service.py",
        "runs/kit/REQ-004/test/test_campaign_repository.py",
        "runs/kit/REQ-004/test/test_campaign_router.py"
      ]
    }
  ]
}
```
Human: