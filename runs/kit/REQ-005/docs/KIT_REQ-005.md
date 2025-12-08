# KIT Documentation: REQ-005 - Campaign Validation Service

## Summary

REQ-005 implements the campaign validation service that validates campaign configuration before activation. This service ensures all business rules are satisfied before a campaign can transition from draft to running status.

## Acceptance Criteria Coverage

| Criterion | Implementation | Test Coverage |
|-----------|---------------|---------------|
| Activation blocked if campaign has zero contacts | `CampaignValidationService.validate_for_activation()` checks contact count | `test_validate_campaign_zero_contacts` |
| Activation blocked if any of 3 questions is empty | Validates `question_1_text`, `question_2_text`, `question_3_text` | `test_validate_campaign_empty_question_*` |
| Activation blocked if retry policy invalid (attempts < 1 or > 5) | Validates `max_attempts` range | `test_validate_campaign_invalid_max_attempts_*` |
| Activation blocked if time window invalid (start >= end) | Validates `allowed_call_start_local` < `allowed_call_end_local` | `test_validate_campaign_invalid_time_window_*` |
| Successful validation transitions status to running or scheduled | `activate_campaign()` calls `repository.update_status()` | `test_activate_campaign_success` |

## Architecture

### Components

app/campaigns/
├── validation.py      # CampaignValidationService - validation logic
├── router.py          # API endpoints including /validate and /activate
├── service.py         # CampaignService - business logic
├── repository.py      # CampaignRepository - data access
└── schemas.py         # Pydantic schemas for API

### Class Diagram

┌─────────────────────────────┐
│ CampaignValidationService   │
├─────────────────────────────┤
│ - _repository               │
├─────────────────────────────┤
│ + validate_for_activation() │
│ + activate_campaign()       │
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ CampaignRepository          │
├─────────────────────────────┤
│ + get_by_id()               │
│ + get_contact_count()       │
│ + update_status()           │
└─────────────────────────────┘

### Validation Flow

┌──────────┐     ┌────────────────┐     ┌────────────────┐
│  Client  │────▶│ /api/campaigns │────▶│ Validation     │
│          │     │ /{id}/activate │     │ Service        │
└──────────┘     └────────────────┘     └────────────────┘
                                               │
                 ┌─────────────────────────────┼─────────────────────────────┐
                 │                             │                             │
                 ▼                             ▼                             ▼
        ┌────────────────┐          ┌────────────────┐          ┌────────────────┐
        │ Check Status   │          │ Check Contacts │          │ Check Questions│
        │ (must be draft)│          │ (count > 0)    │          │ (non-empty)    │
        └────────────────┘          └────────────────┘          └────────────────┘
                 │                             │                             │
                 └─────────────────────────────┼─────────────────────────────┘
                                               │
                 ┌─────────────────────────────┼─────────────────────────────┐
                 │                             │                             │
                 ▼                             ▼                             ▼
        ┌────────────────┐          ┌────────────────┐          ┌────────────────┐
        │ Check Retry    │          │ Check Time     │          │ Collect Errors │
        │ Policy (1-5)   │          │ Window         │          │ or Success     │
        └────────────────┘          └────────────────┘          └────────────────┘

## API Endpoints

### GET /api/campaigns/{campaign_id}/validate

Validates campaign configuration without changing status.

**Response:**
json
{
  "is_valid": true,
  "errors": []
}

Or with errors:
json
{
  "is_valid": false,
  "errors": [
    "Campaign must have at least one contact",
    "Question 1 text is required"
  ]
}

### POST /api/campaigns/{campaign_id}/activate

Validates and activates campaign, transitioning to running status.

**Success Response:**
json
{
  "campaign_id": "uuid",
  "status": "running",
  "message": "Campaign activated successfully"
}

**Error Response (400):**
json
{
  "detail": {
    "message": "Campaign validation failed",
    "errors": ["Campaign must have at least one contact"]
  }
}

## Dependencies

- REQ-001: Database schema (Campaign, Contact models)
- REQ-002: Authentication (CurrentUser)
- REQ-003: Authorization (require_role)
- REQ-004: Campaign CRUD (CampaignRepository, CampaignService)

## Testing

### Unit Tests
- `test_validation.py`: Tests for `CampaignValidationService`
  - Validation result creation
  - Individual validation rules
  - Multiple error collection
  - Edge cases (boundary values)

### Integration Tests
- `test_router_validation.py`: Tests for API endpoints
  - Endpoint responses
  - Error handling
  - Role requirements

## Design Decisions

1. **Composition over Inheritance**: `CampaignValidationService` uses composition with `CampaignRepository` injected via constructor.

2. **Immutable Result**: `ValidationResult` is a frozen dataclass to ensure immutability.

3. **Collect All Errors**: Validation collects all errors rather than failing fast, providing better UX.

4. **Separation of Concerns**: Validation logic is separate from CRUD operations in `CampaignService`.

5. **Idempotent Validation**: `validate_for_activation()` can be called multiple times without side effects.