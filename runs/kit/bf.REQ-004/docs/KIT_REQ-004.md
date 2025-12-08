# KIT Documentation: REQ-004 - Campaign CRUD API

## Overview

REQ-004 implements the Campaign CRUD API for the VoiceSurveyAgent system. This module provides REST endpoints for creating, reading, updating, and deleting survey campaigns with proper state machine validation.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| POST /api/campaigns creates campaign in draft status | ✅ | `router.py:create_campaign()` |
| GET /api/campaigns returns paginated list with status filter | ✅ | `router.py:list_campaigns()` |
| GET /api/campaigns/{id} returns full campaign details | ✅ | `router.py:get_campaign()` |
| PUT /api/campaigns/{id} validates field changes against current status | ✅ | `service.py:update_campaign()` |
| Status transitions follow state machine | ✅ | `service.py:VALID_TRANSITIONS` |

## Architecture

### Module Structure

app/campaigns/
├── __init__.py      # Module exports
├── models.py        # SQLAlchemy ORM models
├── schemas.py       # Pydantic request/response schemas
├── repository.py    # Data access layer
├── service.py       # Business logic and state machine
└── router.py        # FastAPI endpoints

### Dependencies
- **REQ-001**: Database schema (Campaign, User tables)
- **REQ-003**: RBAC middleware (role-based access control)

### State Machine

draft ──────┬──────> scheduled ──────┬──────> running ──────┬──────> completed
            │                        │                      │
            │                        └──────> paused ───────┘
            │                                   │
            └──────> running                    │
            │                                   │
            └──────> cancelled <────────────────┴──────────────────────────────

## API Endpoints

### POST /api/campaigns
Creates a new campaign in draft status.

**Authorization:** `campaign_manager`, `admin`

**Request Body:**
json
{
  "name": "string",
  "description": "string",
  "language": "en|it",
  "intro_script": "string",
  "question_1": {"text": "string", "type": "free_text|numeric|scale"},
  "question_2": {"text": "string", "type": "free_text|numeric|scale"},
  "question_3": {"text": "string", "type": "free_text|numeric|scale"},
  "max_attempts": 1-5,
  "retry_interval_minutes": integer,
  "allowed_call_start_local": "HH:MM:SS",
  "allowed_call_end_local": "HH:MM:SS"
}

### GET /api/campaigns
Lists campaigns with pagination and optional status filter.

**Authorization:** `viewer`, `campaign_manager`, `admin`

**Query Parameters:**
- `status`: Filter by campaign status
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

### GET /api/campaigns/{id}
Returns full campaign details.

**Authorization:** `viewer`, `campaign_manager`, `admin`

### PUT /api/campaigns/{id}
Updates campaign fields based on current status restrictions.

**Authorization:** `campaign_manager`, `admin`

**Field Restrictions by Status:**
- `draft`: All fields editable
- `scheduled/running/paused`: Only name, description, email templates
- `completed/cancelled`: No fields editable

### DELETE /api/campaigns/{id}
Soft deletes campaign by setting status to cancelled.

**Authorization:** `campaign_manager`, `admin`

### POST /api/campaigns/{id}/status
Transitions campaign to a new status.

**Authorization:** `campaign_manager`, `admin`

## Testing

### Test Coverage
- Unit tests for service layer business logic
- Integration tests for API endpoints
- State machine transition validation
- RBAC enforcement tests

### Running Tests
bash
cd runs/kit/REQ-004
pytest test/ -v --cov=src/app

## Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection URL | postgresql://... |
| APP_ENV | Application environment | dev |
| LOG_LEVEL | Logging level | INFO |
| DEFAULT_PAGE_SIZE | Default pagination size | 20 |
| MAX_PAGE_SIZE | Maximum pagination size | 100 |

## Error Handling

### Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Invalid request data |
| INVALID_STATE_TRANSITION | 400 | Invalid status transition |
| AUTHENTICATION_ERROR | 401 | Missing or invalid token |
| AUTHORIZATION_ERROR | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Campaign not found |