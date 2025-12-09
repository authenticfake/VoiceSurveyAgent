# REQ-005: Campaign Validation Service

## Overview

This module implements campaign validation logic that must pass before a campaign can be activated. It ensures campaigns have proper configuration including contacts, questions, retry policies, and time windows.

## Quick Start

bash
# Install dependencies
cd runs/kit/REQ-005
pip install -r requirements.txt

# Set environment
export PYTHONPATH="src:../REQ-004/src:../REQ-003/src:../REQ-002/src:../REQ-001/src"

# Run tests
pytest test -v

## Features

- **Contact Validation**: Ensures campaign has at least one contact
- **Question Validation**: Verifies all three questions are non-empty
- **Retry Policy Validation**: Checks max_attempts is between 1-5
- **Time Window Validation**: Ensures call start time is before end time
- **Status Validation**: Only draft campaigns can be activated

## Usage

### Validate a Campaign

python
from app.campaigns.validation import CampaignValidationService
from app.campaigns.repository import CampaignRepository

repository = CampaignRepository(session)
validation_service = CampaignValidationService(repository)

result = await validation_service.validate_for_activation(campaign_id)
if result.is_valid:
    print("Campaign is ready for activation")
else:
    for error in result.errors:
        print(f"{error.field}: {error.message}")

### Activate a Campaign

python
from app.campaigns.service import CampaignService

service = CampaignService(repository)
try:
    campaign = await service.activate_campaign(campaign_id)
    print(f"Campaign activated: {campaign.status}")
except ValidationError as e:
    print(f"Validation failed: {e}")

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/campaigns/{id}/validate` | Check if campaign can be activated |
| POST | `/api/campaigns/{id}/activate` | Validate and activate campaign |

## Error Codes

| Code | Description |
|------|-------------|
| NO_CONTACTS | Campaign has no contacts |
| EMPTY_QUESTION | One or more questions are empty |
| INVALID_RETRY_POLICY | max_attempts not in range 1-5 |
| INVALID_TIME_WINDOW | Call start time >= end time |
| INVALID_STATUS | Campaign not in draft status |

## Dependencies

- REQ-001: Database models
- REQ-002: Authentication
- REQ-003: Authorization
- REQ-004: Campaign CRUD

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-005**: Campaign validation service

### Rationale
REQ-005 depends on REQ-004 (Campaign CRUD API) which is marked as in_progress. This REQ extends the campaign module with validation logic that blocks activation based on specific business rules.

### In Scope
- Campaign validation service with all acceptance criteria
- Validation for: contacts count, questions, retry policy, time window, status
- Extended campaign service with `validate_for_activation()` and `activate_campaign()`
- New API endpoints: `GET /validate` and `POST /activate`
- Comprehensive unit tests for validation logic
- Integration tests for service and router layers

### Out of Scope
- Database integration tests (requires running PostgreSQL)
- Frontend validation UI
- Email template validation

### How to Run Tests
bash
cd runs/kit/REQ-005
export PYTHONPATH="src:../REQ-004/src:../REQ-003/src:../REQ-002/src:../REQ-001/src"
pip install -r requirements.txt
pytest test -v

### Prerequisites
- Python 3.12+
- Dependencies from requirements.txt
- PYTHONPATH set to include dependent REQ source directories

### Dependencies and Mocks
- **CampaignDataProvider Protocol**: Defines interface for data access, implemented by repository
- **MockDataProvider**: Test implementation for unit testing validation logic
- **AsyncMock**: Used for mocking repository and service in integration tests

### Product Owner Notes
- Validation runs synchronously on activation request as specified
- All validation errors are collected and returned together (except status check which returns early)
- Whitespace-only questions are treated as empty

### RAG Citations
- Used REQ-004 campaign schemas and service patterns
- Used REQ-001 database models for Contact and Campaign
- Used REQ-002/REQ-003 auth middleware patterns for router

json
{
  "index": [
    {
      "req": "REQ-005",
      "src": [
        "runs/kit/REQ-005/src/app/campaigns/validation.py",
        "runs/kit/REQ-005/src/app/campaigns/schemas.py",
        "runs/kit/REQ-005/src/app/campaigns/repository.py",
        "runs/kit/REQ-005/src/app/campaigns/service.py",
        "runs/kit/REQ-005/src/app/campaigns/router.py",
        "runs/kit/REQ-005/src/app/campaigns/__init__.py"
      ],
      "tests": [
        "runs/kit/REQ-005/test/test_validation.py",
        "runs/kit/REQ-005/test/test_service_activation.py",
        "runs/kit/REQ-005/test/test_router_validation.py"
      ]
    }
  ]
}

Human: