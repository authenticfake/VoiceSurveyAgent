# KIT Documentation: REQ-004 - Campaign CRUD API

## Overview
This KIT implements the Campaign CRUD API for the Voice Survey Agent system. It provides RESTful endpoints for creating, reading, updating, and deleting survey campaigns with proper state machine management.

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
```
app/campaigns/
├── __init__.py      # Module exports
├── router.py        # FastAPI endpoints
├── service.py       # Business logic
├── repository.py    # Database operations
└── schemas.py       # Pydantic models
```

### Dependencies
- REQ-001: Database models and migrations
- REQ-002: OIDC authentication
- REQ-003: RBAC authorization

### State Machine
```
draft → scheduled → running → paused → running
  ↓         ↓          ↓         ↓
  └─────────┴──────────┴─────────┴──→ cancelled
                       ↓
                   completed
```

## API Endpoints

| Method | Path | Description | Required Role |
|--------|------|-------------|---------------|
| POST | /api/campaigns | Create campaign | campaign_manager |
| GET | /api/campaigns | List campaigns | viewer |
| GET | /api/campaigns/{id} | Get campaign | viewer |
| PUT | /api/campaigns/{id} | Update campaign | campaign_manager |
| PATCH | /api/campaigns/{id}/status | Update status | campaign_manager |
| DELETE | /api/campaigns/{id} | Soft delete | campaign_manager |

## Testing

### Test Coverage
- Schema validation tests
- Service layer unit tests
- Repository integration tests
- API endpoint tests

### Running Tests
```bash
export PYTHONPATH=runs/kit/REQ-001/src:runs/kit/REQ-002/src:runs/kit/REQ-003/src:runs/kit/REQ-004/src
pytest runs/kit/REQ-004/test -v --cov=app.campaigns
```

## Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | Database connection string | Required |
| LOG_LEVEL | Logging level | INFO |

## Error Handling

| Error | HTTP Status | Description |
|-------|-------------|-------------|
| NotFoundError | 404 | Campaign not found |
| ValidationError | 400 | Invalid field values or status |
| StateTransitionError | 400 | Invalid status transition |