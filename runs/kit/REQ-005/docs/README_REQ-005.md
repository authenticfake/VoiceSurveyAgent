# REQ-005: Campaign Validation Service

## Purpose

Validates campaign configuration before activation to ensure all business requirements are met. Prevents campaigns from being activated with invalid or incomplete configuration.

## Quick Start

```bash
# Set environment
export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install dependencies
pip install -r runs/kit/REQ-005/requirements.txt

# Run tests
pytest runs/kit/REQ-005/test/ -v
```

## Key Components

### CampaignValidationService

Main service class that performs validation:

```python
from app.campaigns.validation import CampaignValidationService

service = CampaignValidationService(
    campaign_repository=campaign_repo,
    contact_repository=contact_repo,
)

# Validate without activating
result = await service.validate_for_activation(campaign_id)
if not result.is_valid:
    print(result.errors)

# Validate and activate
campaign = await service.activate_campaign(campaign_id)
```

### ValidationResult

Collects validation errors:

```python
from app.campaigns.validation import ValidationResult

result = ValidationResult()
result.add_error("field_name", "Error message")

if not result.is_valid:
    for error in result.errors:
        print(f"{error['field']}: {error['message']}")
```

### API Endpoint

```bash
# Activate a campaign
curl -X POST "http://localhost:8000/api/campaigns/{id}/activate" \
  -H "Authorization: Bearer <token>"
```

## Validation Rules

1. **Contacts**: Must have at least 1 contact
2. **Questions**: All 3 questions must be non-empty
3. **Retry Policy**: max_attempts must be 1-5
4. **Time Window**: Start time must be before end time

## Error Handling

Validation errors return structured responses:

```json
{
  "code": "VALIDATION_FAILED",
  "message": "Campaign validation failed",
  "errors": [
    {"field": "contacts", "message": "Campaign must have at least one contact"}
  ]
}
```

## Testing

```bash
# Unit tests
pytest runs/kit/REQ-005/test/test_validation_service.py -v

# API tests
pytest runs/kit/REQ-005/test/test_activation_api.py -v

# With coverage
pytest runs/kit/REQ-005/test/ --cov=runs/kit/REQ-005/src
```
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-005**: Campaign validation service

### Rationale
REQ-005 depends on REQ-004 (Campaign CRUD API) which is marked as `in_progress`. This REQ implements the validation logic that must run before a campaign can be activated, ensuring all business rules are enforced.

### In Scope
- Campaign validation service with all 5 acceptance criteria
- Validation for: zero contacts, empty questions, invalid retry policy, invalid time window
- Status transition from `draft` to `running` on successful validation
- API endpoint `POST /api/campaigns/{id}/activate`
- Unit tests for validation logic
- Integration tests for API endpoint
- Contact repository with `count_by_campaign` method
- Contact model (minimal, for validation support)
- Extended ValidationError with details field
- Extended schemas with ValidationErrorResponse

### Out of Scope
- Full contact CRUD operations (REQ-006)
- Contact CSV upload (REQ-006)
- Exclusion list management (REQ-007)
- Scheduled status (only immediate activation to `running` implemented)

### How to Run Tests

```bash
# Set PYTHONPATH to include all dependencies
export PYTHONPATH="runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install test dependencies
pip install -r runs/kit/REQ-005/requirements.txt

# Run all tests
pytest runs/kit/REQ-005/test/ -v

# Run with coverage
pytest runs/kit/REQ-005/test/ -v --cov=runs/kit/REQ-005/src --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- pytest >= 8.0
- pytest-asyncio >= 0.23
- httpx >= 0.27
- Previous REQs (001-004) source code in PYTHONPATH

### Dependencies and Mocks
- **CampaignRepository**: Mocked in unit tests via AsyncMock
- **ContactRepository**: Mocked in unit tests via AsyncMock
- **Database**: Not required for unit tests (all mocked)
- **Authentication**: Mocked in API tests via patch

### Product Owner Notes
- Validation collects ALL errors before returning, not just the first one
- Time window validation requires start < end (not <=)
- Only `draft` status campaigns can be activated
- Activation immediately transitions to `running` (scheduled activation deferred)

### RAG Citations
- `runs/kit/REQ-004/src/app/campaigns/models.py` - Campaign model structure
- `runs/kit/REQ-004/src/app/campaigns/repository.py` - CampaignRepository pattern
- `runs/kit/REQ-003/src/app/auth/rbac.py` - RBAC decorator pattern
- `runs/kit/REQ-002/src/app/shared/exceptions.py` - Exception patterns
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Contact table schema

```json
{
  "index": [
    {
      "req": "REQ-005",
      "src": [
        "runs/kit/REQ-005/src/app/campaigns/validation.py",
        "runs/kit/REQ-005/src/app/campaigns/activation_router.py",
        "runs/kit/REQ-005/src/app/campaigns/schemas.py",
        "runs/kit/REQ-005/src/app/campaigns/models.py",
        "runs/kit/REQ-005/src/app/contacts/__init__.py",
        "runs/kit/REQ-005/src/app/contacts/repository.py",
        "runs/kit/REQ-005/src/app/contacts/models.py",
        "runs/kit/REQ-005/src/app/shared/exceptions.py"
      ],
      "tests": [
        "runs/kit/REQ-005/test/test_validation_service.py",
        "runs/kit/REQ-005/test/test_activation_api.py",
        "runs/kit/REQ-005/test/conftest.py"
      ]
    }
  ]
}