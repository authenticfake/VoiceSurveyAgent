# REQ-004: Campaign CRUD API

## Overview

This module implements the Campaign CRUD API for the VoiceSurveyAgent system, providing endpoints for creating, reading, updating, and deleting survey campaigns.

## Features

- **Create Campaign**: Create new campaigns in draft status
- **List Campaigns**: Paginated listing with status filter
- **Get Campaign**: Retrieve full campaign details
- **Update Campaign**: Modify campaign fields (with status-based restrictions)
- **Delete Campaign**: Soft delete by setting status to cancelled
- **Status Transitions**: Manage campaign lifecycle through state machine

## Quick Start

### Installation

```bash
pip install -r runs/kit/REQ-004/requirements.txt
```

### Running Tests

```bash
export PYTHONPATH=runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src
pytest runs/kit/REQ-004/test -v
```

### API Usage

```python
from app.campaigns.service import CampaignService
from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import CampaignCreate

# Create service
repository = CampaignRepository(session)
service = CampaignService(repository)

# Create campaign
data = CampaignCreate(
    name="My Survey",
    intro_script="Hello...",
    question_1_text="How satisfied are you?",
    question_1_type="scale",
    question_2_text="What could we improve?",
    question_2_type="free_text",
    question_3_text="Would you recommend us?",
    question_3_type="numeric",
    allowed_call_start_local=time(9, 0),
    allowed_call_end_local=time(18, 0),
)
campaign = await service.create_campaign(data, user_id)
```

## Dependencies

- REQ-001: Database schema
- REQ-002: OIDC authentication
- REQ-003: RBAC authorization

## Documentation

- [KIT Documentation](./KIT_REQ-004.md) - Detailed implementation documentation
- [API Collection](../test/api/campaigns.json) - API request examples
- [HOWTO](../ci/HOWTO.md) - Execution guide
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-004**: Campaign CRUD API

### Rationale
REQ-004 depends on REQ-003 (RBAC authorization middleware) which is marked as `in_progress`. The implementation builds on the authentication and authorization infrastructure from REQ-002 and REQ-003 to provide protected campaign management endpoints.

### In Scope
- Campaign SQLAlchemy model with status state machine
- Pydantic schemas for request/response validation
- Repository layer for database operations
- Service layer for business logic
- FastAPI router with CRUD endpoints
- Status transition endpoint with validation
- Unit tests for model, service, and schemas
- API integration tests
- LTC.json for CI execution
- HOWTO.md for execution guide
- API collection for manual testing

### Out of Scope
- Campaign validation service (REQ-005)
- Contact CSV upload (REQ-006)
- Integration with actual database (tests use mocks)
- Frontend components

### How to Run Tests

```bash
# Set PYTHONPATH to include all required modules
export PYTHONPATH=runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src

# Install dependencies
pip install -r runs/kit/REQ-004/requirements.txt

# Run all tests
pytest runs/kit/REQ-004/test -v

# Run with coverage
pytest runs/kit/REQ-004/test -v --cov=app.campaigns --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ (for integration tests)
- Dependencies from REQ-002 and REQ-003 installed

### Dependencies and Mocks
- **Database Session**: Mocked using AsyncMock for unit and API tests
- **Authentication**: Mocked `get_current_user` dependency to simulate authenticated users
- **Campaign Service**: Mocked in API tests to isolate endpoint testing

### Product Owner Notes
- Status transitions follow the state machine defined in SPEC: draft→scheduled→running→paused→completed
- Soft delete implemented (sets status to cancelled) rather than hard delete
- Field update restrictions enforced based on campaign status
- All endpoints require authentication; write operations require campaign_manager or admin role

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Campaign table schema reference
- `runs/kit/REQ-002/src/app/auth/middleware.py` - Authentication middleware patterns
- `runs/kit/REQ-003/src/app/auth/rbac.py` - RBAC decorator patterns
- `runs/kit/REQ-002/src/app/shared/exceptions.py` - Exception patterns extended

```json
{
  "index": [
    {
      "req": "REQ-004",
      "src": [
        "runs/kit/REQ-004/src/app/campaigns/__init__.py",
        "runs/kit/REQ-004/src/app/campaigns/models.py",
        "runs/kit/REQ-004/src/app/campaigns/schemas.py",
        "runs/kit/REQ-004/src/app/campaigns/repository.py",
        "runs/kit/REQ-004/src/app/campaigns/service.py",
        "runs/kit/REQ-004/src/app/campaigns/router.py",
        "runs/kit/REQ-004/src/app/shared/exceptions.py",
        "runs/kit/REQ-004/src/app/main.py"
      ],
      "tests": [
        "runs/kit/REQ-004/test/test_campaigns_unit.py",
        "runs/kit/REQ-004/test/test_campaigns_api.py",
        "runs/kit/REQ-004/test/conftest.py"
      ]
    }
  ]
}