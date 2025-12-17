# KIT Documentation - REQ-004: Campaign CRUD API

## Summary

REQ-004 implements the Campaign CRUD API for the VoiceSurveyAgent system. This includes creating, reading, updating, and deleting campaigns, as well as managing campaign status transitions following a defined state machine.

## Acceptance Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| POST /api/campaigns creates campaign in draft status | ✅ Implemented | Always creates in draft status |
| GET /api/campaigns returns paginated list with status filter | ✅ Implemented | Supports page, page_size, status params |
| GET /api/campaigns/{id} returns full campaign details | ✅ Implemented | Returns all campaign fields |
| PUT /api/campaigns/{id} validates field changes against current status | ✅ Implemented | Draft-only fields enforced |
| Status transitions follow state machine | ✅ Implemented | draft→scheduled→running→paused→completed |

## Architecture

### Module Structure

```
app/campaigns/
├── __init__.py      # Module exports
├── models.py        # SQLAlchemy Campaign model
├── schemas.py       # Pydantic request/response schemas
├── repository.py    # Database operations
├── service.py       # Business logic
└── router.py        # FastAPI endpoints
```

### Dependencies

- **REQ-001**: Database schema (Campaign table)
- **REQ-002**: Authentication (JWT validation)
- **REQ-003**: Authorization (RBAC middleware)

### Key Design Decisions

1. **Soft Delete**: DELETE operation sets status to `cancelled` rather than removing the record
2. **Status State Machine**: Enforced at service layer with clear valid transitions
3. **Field Update Restrictions**: Core campaign fields (questions, retry policy) can only be updated in draft status
4. **Pagination**: Default page size of 20, max 100

## API Endpoints

### POST /api/campaigns
Creates a new campaign in draft status.

**Required Role**: campaign_manager, admin

**Request Body**:
```json
{
  "name": "string",
  "description": "string (optional)",
  "language": "en|it",
  "intro_script": "string",
  "question_1_text": "string",
  "question_1_type": "free_text|numeric|scale",
  "question_2_text": "string",
  "question_2_type": "free_text|numeric|scale",
  "question_3_text": "string",
  "question_3_type": "free_text|numeric|scale",
  "max_attempts": 1-5,
  "retry_interval_minutes": integer,
  "allowed_call_start_local": "HH:MM:SS",
  "allowed_call_end_local": "HH:MM:SS"
}
```

### GET /api/campaigns
Returns paginated list of campaigns.

**Required Role**: viewer, campaign_manager, admin

**Query Parameters**:
- `status`: Filter by campaign status
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

### GET /api/campaigns/{id}
Returns full campaign details.

**Required Role**: viewer, campaign_manager, admin

### PUT /api/campaigns/{id}
Updates campaign fields.

**Required Role**: campaign_manager, admin

**Restrictions**:
- Core fields (name, questions, retry policy, time window) can only be updated in draft status
- Description and email template IDs can be updated in any status

### DELETE /api/campaigns/{id}
Soft deletes campaign by setting status to cancelled.

**Required Role**: campaign_manager, admin

### POST /api/campaigns/{id}/status
Transitions campaign to a new status.

**Required Role**: campaign_manager, admin

**Valid Transitions**:
- draft → scheduled, running, cancelled
- scheduled → running, paused, cancelled
- running → paused, completed, cancelled
- paused → running, cancelled
- completed → (none - terminal)
- cancelled → (none - terminal)

## Status State Machine

```
                    ┌─────────────┐
                    │    draft    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌───────────┐
        │scheduled │ │ running  │ │ cancelled │
        └────┬─────┘ └────┬─────┘ └───────────┘
             │            │
             └─────┬──────┘
                   ▼
             ┌──────────┐
             │  paused  │
             └────┬─────┘
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
  ┌──────────┐ ┌───────────┐
  │ running  │ │ cancelled │
  └────┬─────┘ └───────────┘
       │
       ▼
  ┌───────────┐
  │ completed │
  └───────────┘
```

## Error Handling

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| CAMPAIGN_NOT_FOUND | 404 | Campaign with given ID does not exist |
| VALIDATION_ERROR | 400 | Request validation failed |
| INVALID_STATUS_TRANSITION | 400 | Status transition not allowed |
| INSUFFICIENT_PERMISSIONS | 403 | User lacks required role |

## Testing

### Unit Tests
- Model status transition logic
- Service business logic
- Schema validation

### API Tests
- Endpoint functionality
- RBAC enforcement
- Error responses

### Running Tests
```bash
export PYTHONPATH=runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src
pytest runs/kit/REQ-004/test -v --cov=app.campaigns