# KIT Documentation: REQ-005 - Campaign Validation Service

## Summary

REQ-005 implements the campaign validation service that validates campaign configuration before activation. This ensures campaigns meet all business requirements before transitioning from `draft` to `running` status.

## Acceptance Criteria Coverage

| Criterion | Implementation | Status |
|-----------|----------------|--------|
| Activation blocked if campaign has zero contacts | `CampaignValidationService.validate_for_activation()` checks contact count | ✅ |
| Activation blocked if any of 3 questions is empty | `_validate_questions()` checks all 3 question texts | ✅ |
| Activation blocked if retry policy invalid (attempts < 1 or > 5) | `_validate_retry_policy()` enforces 1-5 range | ✅ |
| Activation blocked if time window invalid (start >= end) | `_validate_time_window()` validates start < end | ✅ |
| Successful validation transitions status to running or scheduled | `activate_campaign()` transitions to RUNNING | ✅ |

## Architecture

### Components

```
app/campaigns/
├── validation.py          # CampaignValidationService, ValidationResult
├── activation_router.py   # POST /api/campaigns/{id}/activate endpoint
├── schemas.py             # Extended with ValidationErrorResponse
└── models.py              # Extended with contacts relationship

app/contacts/
├── __init__.py            # Module exports
├── repository.py          # ContactRepository with count_by_campaign
└── models.py              # Contact model

app/shared/
└── exceptions.py          # Extended ValidationError with details
```

### Class Diagram

```
┌─────────────────────────────┐
│ CampaignValidationService   │
├─────────────────────────────┤
│ - _campaign_repo            │
│ - _contact_repo             │
├─────────────────────────────┤
│ + validate_for_activation() │
│ + activate_campaign()       │
│ - _validate_questions()     │
│ - _validate_retry_policy()  │
│ - _validate_time_window()   │
└─────────────────────────────┘
         │
         │ uses
         ▼
┌─────────────────────────────┐
│ ValidationResult            │
├─────────────────────────────┤
│ - _errors: list             │
│ - _is_valid: bool           │
├─────────────────────────────┤
│ + add_error()               │
│ + is_valid                  │
│ + errors                    │
└─────────────────────────────┘
```

### Dependency Injection

The service follows DIP (Dependency Inversion Principle):

```python
class CampaignValidationService:
    def __init__(
        self,
        campaign_repository: CampaignRepositoryProtocol,
        contact_repository: ContactRepositoryProtocol,
    ) -> None:
```

Both repositories are injected via protocols, enabling:
- Easy unit testing with mocks
- Swappable implementations
- Clear interface contracts

## API Endpoint

### POST /api/campaigns/{campaign_id}/activate

**Request:**
```http
POST /api/campaigns/123e4567-e89b-12d3-a456-426614174000/activate
Authorization: Bearer <jwt_token>
```

**Success Response (200):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Customer Survey Q1",
  "status": "running",
  "language": "en",
  ...
}
```

**Validation Error (400):**
```json
{
  "detail": {
    "code": "VALIDATION_FAILED",
    "message": "Campaign validation failed",
    "errors": [
      {"field": "contacts", "message": "Campaign must have at least one contact"},
      {"field": "question_1_text", "message": "question_1_text cannot be empty"}
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

### 1. Contact Count
- Campaign must have at least one contact
- Checked via `ContactRepository.count_by_campaign()`

### 2. Questions
- All 3 questions must be non-empty
- Whitespace-only strings are considered empty
- Each question validated independently

### 3. Retry Policy
- `max_attempts` must be >= 1 and <= 5
- Enforced at both validation and database constraint level

### 4. Time Window
- `allowed_call_start_local` must be strictly before `allowed_call_end_local`
- Both times must be configured (not null)

## Test Coverage

### Unit Tests (`test_validation_service.py`)
- ValidationResult class behavior
- Campaign not found handling
- Zero contacts validation
- Empty questions validation (all 3)
- Retry policy bounds (< 1, > 5)
- Time window validation (equal, reversed, missing)
- Multiple errors collection
- Successful validation
- Activation flow

### API Tests (`test_activation_api.py`)
- Successful activation
- Validation failure response
- Not found response
- Authentication requirement

## Dependencies

### Upstream (this REQ depends on)
- REQ-001: Database schema (Campaign, Contact tables)
- REQ-002: Authentication (CurrentUser, JWT validation)
- REQ-003: RBAC (require_campaign_manager decorator)
- REQ-004: Campaign CRUD (CampaignRepository, Campaign model)

### Downstream (depends on this REQ)
- REQ-006: Contact CSV upload (uses ContactRepository)
- REQ-008: Call scheduler (uses campaign status)

## Files Created/Modified

### New Files
- `runs/kit/REQ-005/src/app/campaigns/validation.py`
- `runs/kit/REQ-005/src/app/campaigns/activation_router.py`
- `runs/kit/REQ-005/src/app/contacts/__init__.py`
- `runs/kit/REQ-005/src/app/contacts/repository.py`
- `runs/kit/REQ-005/src/app/contacts/models.py`
- `runs/kit/REQ-005/test/test_validation_service.py`
- `runs/kit/REQ-005/test/test_activation_api.py`
- `runs/kit/REQ-005/test/conftest.py`

### Extended Files
- `runs/kit/REQ-005/src/app/campaigns/schemas.py` - Added ValidationErrorResponse
- `runs/kit/REQ-005/src/app/campaigns/models.py` - Added contacts relationship
- `runs/kit/REQ-005/src/app/shared/exceptions.py` - Extended ValidationError