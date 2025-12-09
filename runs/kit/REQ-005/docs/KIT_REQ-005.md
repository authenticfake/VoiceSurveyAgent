# KIT Documentation: REQ-005 - Campaign Validation Service

## Summary

REQ-005 implements the campaign validation service that enforces business rules before a campaign can be activated. This ensures data integrity and prevents campaigns from running with invalid configurations.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| Activation blocked if campaign has zero contacts | ✅ | `CampaignValidationService.validate_for_activation()` |
| Activation blocked if any of 3 questions is empty | ✅ | Question validation in validation service |
| Activation blocked if retry policy invalid (attempts < 1 or > 5) | ✅ | Retry policy validation |
| Activation blocked if time window invalid (start >= end) | ✅ | Time window validation |
| Successful validation transitions status to running or scheduled | ✅ | `CampaignService.activate_campaign()` |

## Architecture

### Components

1. **CampaignValidationService** (`validation.py`)
   - Core validation logic
   - Uses CampaignDataProvider protocol for data access
   - Returns structured ValidationResult

2. **CampaignDataProvider Protocol** (`validation.py`)
   - Defines interface for campaign data access
   - Implemented by CampaignRepository

3. **Extended CampaignService** (`service.py`)
   - `validate_for_activation()` - Returns validation result
   - `activate_campaign()` - Validates and transitions to running

4. **Extended Router** (`router.py`)
   - `GET /api/campaigns/{id}/validate` - Check validation status
   - `POST /api/campaigns/{id}/activate` - Validate and activate

### Validation Rules

| Rule | Field | Code | Message |
|------|-------|------|---------|
| Status must be draft | status | INVALID_STATUS | Campaign must be in draft status |
| Must have contacts | contacts | NO_CONTACTS | Campaign must have at least one contact |
| Question 1 required | question_1_text | EMPTY_QUESTION | Question 1 cannot be empty |
| Question 2 required | question_2_text | EMPTY_QUESTION | Question 2 cannot be empty |
| Question 3 required | question_3_text | EMPTY_QUESTION | Question 3 cannot be empty |
| Valid retry attempts | max_attempts | INVALID_RETRY_POLICY | Must be between 1 and 5 |
| Valid time window | allowed_call_start_local | INVALID_TIME_WINDOW | Start must be before end |

## Dependencies

- REQ-001: Database schema (Contact model for count)
- REQ-002: Authentication (user context)
- REQ-003: RBAC (campaign_manager role required)
- REQ-004: Campaign CRUD (base service and repository)

## Testing

### Test Coverage

- `test_validation.py`: Unit tests for validation service
- `test_service_activation.py`: Service layer activation tests
- `test_router_validation.py`: API endpoint tests

### Running Tests

bash
cd runs/kit/REQ-005
export PYTHONPATH="src:../REQ-004/src:../REQ-003/src:../REQ-002/src:../REQ-001/src"
pytest test -v

## API Reference

### Validate Campaign

http
GET /api/campaigns/{campaign_id}/validate
Authorization: Bearer <token>

Response:
json
{
  "is_valid": true,
  "errors": []
}

### Activate Campaign

http
POST /api/campaigns/{campaign_id}/activate
Authorization: Bearer <token>

Success Response:
json
{
  "campaign_id": "uuid",
  "status": "running",
  "message": "Campaign activated successfully"
}

Error Response (400):
json
{
  "detail": "Campaign validation failed: contacts: Campaign must have at least one contact"
}