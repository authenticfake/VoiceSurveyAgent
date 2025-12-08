# REQ-005: Campaign Validation Service

## Overview

This module implements campaign validation logic that ensures campaigns meet all business requirements before activation. It validates contacts, questions, retry policy, and time windows.

## Quick Start

python
from app.campaigns.validation import CampaignValidationService
from app.campaigns.repository import CampaignRepository

# Create service with repository
repository = CampaignRepository(db_session)
validation_service = CampaignValidationService(repository)

# Validate campaign
result = await validation_service.validate_for_activation(campaign_id)
if result.is_valid:
    print("Campaign is ready for activation")
else:
    print(f"Validation errors: {result.errors}")

# Validate and activate
await validation_service.activate_campaign(campaign_id)

## Validation Rules

| Rule | Description | Error Message |
|------|-------------|---------------|
| Status Check | Campaign must be in draft status | "Campaign must be in draft status to activate" |
| Contact Count | At least one contact required | "Campaign must have at least one contact" |
| Question 1 | Non-empty text required | "Question 1 text is required" |
| Question 2 | Non-empty text required | "Question 2 text is required" |
| Question 3 | Non-empty text required | "Question 3 text is required" |
| Max Attempts | Must be between 1 and 5 | "Max attempts must be between 1 and 5" |
| Time Window | Start must be before end | "Call start time must be before end time" |

## API Usage

### Validate Campaign
bash
curl -X GET "http://localhost:8000/api/campaigns/{id}/validate" \
  -H "Authorization: Bearer $TOKEN"

### Activate Campaign
bash
curl -X POST "http://localhost:8000/api/campaigns/{id}/activate" \
  -H "Authorization: Bearer $TOKEN"

### Pause Campaign
bash
curl -X POST "http://localhost:8000/api/campaigns/{id}/pause" \
  -H "Authorization: Bearer $TOKEN"

## Module Structure

runs/kit/REQ-005/
├── src/
│   └── app/
│       ├── campaigns/
│       │   ├── validation.py    # Validation service
│       │   ├── router.py        # API endpoints
│       │   ├── service.py       # Business logic
│       │   ├── repository.py    # Data access
│       │   └── schemas.py       # API schemas
│       └── shared/
│           └── exceptions.py    # Custom exceptions
├── test/
│   ├── test_validation.py       # Unit tests
│   └── test_router_validation.py # Integration tests
├── ci/
│   ├── LTC.json                 # Test contract
│   └── HOWTO.md                 # Execution guide
├── docs/
│   ├── KIT_REQ-005.md           # Technical documentation
│   └── README_REQ-005.md        # This file
└── requirements.txt             # Dependencies

## Dependencies

This module depends on:
- REQ-001: Database models
- REQ-002: Authentication
- REQ-003: Authorization
- REQ-004: Campaign CRUD operations

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-005**: Campaign validation service

### Rationale
REQ-005 is the next open REQ in the dependency chain. It depends on REQ-004 (Campaign CRUD API) which is marked as `in_progress`. The validation service extends the campaign module with activation validation logic.

### In Scope
- Campaign validation service (`CampaignValidationService`)
- Validation rules for:
  - Zero contacts check
  - Empty questions check (all 3)
  - Invalid retry policy (attempts < 1 or > 5)
  - Invalid time window (start >= end)
- API endpoints:
  - `GET /api/campaigns/{id}/validate`
  - `POST /api/campaigns/{id}/activate`
  - `POST /api/campaigns/{id}/pause`
- Unit tests for validation logic
- Integration tests for API endpoints
- Updated schemas for validation responses

### Out of Scope
- Database migrations (handled by REQ-001)
- Authentication/authorization implementation (handled by REQ-002/REQ-003)
- Campaign CRUD operations (handled by REQ-004)
- Contact management (handled by REQ-006)

### How to Run Tests
bash
# Set PYTHONPATH
export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install dependencies
pip install -r runs/kit/REQ-005/requirements.txt

# Run unit tests
pytest runs/kit/REQ-005/test/test_validation.py -v

# Run all tests with coverage
pytest runs/kit/REQ-005/test/ --cov=runs/kit/REQ-005/src --cov-report=term-missing -v

### Prerequisites
- Python 3.12+
- pytest >= 8.0
- pytest-asyncio >= 0.23
- httpx >= 0.27 (for async API tests)

### Dependencies and Mocks
- `CampaignRepository` is mocked in unit tests using `AsyncMock`
- `Campaign` model is mocked using `MagicMock` with spec
- No real database connection required for unit tests
- Integration tests use FastAPI TestClient with mocked dependencies

### Product Owner Notes
- Validation collects all errors rather than failing fast, providing better UX for campaign managers
- The validation endpoint (`/validate`) allows checking without side effects
- The activation endpoint (`/activate`) combines validation and status transition atomically
- Time window validation uses simple comparison; timezone handling is deferred to call scheduling

### RAG Citations
- `runs/kit/REQ-001/src/app/shared/models/campaign.py` - Campaign model structure
- `runs/kit/REQ-001/src/app/shared/models/enums.py` - CampaignStatus enum
- `runs/kit/REQ-004/src/app/campaigns/schemas.py` - Existing campaign schemas
- `runs/kit/REQ-004/src/app/campaigns/router.py` - Existing router patterns
- `docs/harper/lane-guides/python.md` - Python lane guide for testing patterns

### Index
json
{
  "index": [
    {
      "req": "REQ-005",
      "src": [
        "runs/kit/REQ-005/src/app/campaigns/validation.py",
        "runs/kit/REQ-005/src/app/campaigns/router.py",
        "runs/kit/REQ-005/src/app/campaigns/schemas.py",
        "runs/kit/REQ-005/src/app/campaigns/repository.py",
        "runs/kit/REQ-005/src/app/campaigns/service.py",
        "runs/kit/REQ-005/src/app/shared/exceptions.py"
      ],
      "tests": [
        "runs/kit/REQ-005/test/test_validation.py",
        "runs/kit/REQ-005/test/test_router_validation.py"
      ]
    }
  ]
}