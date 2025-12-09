# KIT Documentation — REQ-020: Call Detail View API

## Overview

REQ-020 implements the call detail view API endpoint (`GET /api/calls/{call_id}`) that allows authorized users to retrieve detailed information about specific call attempts, including outcome, timestamps, transcript snippets, and recording URLs.

## Acceptance Criteria Coverage

| Criterion | Implementation | Status |
|-----------|---------------|--------|
| GET /api/calls/{call_id} returns call details | `router.py` - `get_call_detail` endpoint | ✅ |
| Response includes outcome, attempt_number, timestamps | `models.py` - `CallDetailResponse` | ✅ |
| Transcript snippet included if stored | `service.py` - fetches from repository | ✅ |
| Access restricted to campaign_manager and admin | `router.py` - `require_campaign_manager_or_admin` | ✅ |
| 404 returned for non-existent call_id | `router.py` - catches `CallNotFoundError` | ✅ |

## Architecture

### Module Structure

```
runs/kit/REQ-020/src/app/calls/
├── __init__.py          # Module exports
├── models.py            # Pydantic models (CallDetailResponse, TranscriptSnippet)
├── exceptions.py        # Domain exceptions (CallNotFoundError, CallAccessDeniedError)
├── repository.py        # Data access layer (CallRepository protocol + Postgres impl)
├── service.py           # Business logic (CallDetailService)
└── router.py            # FastAPI router with RBAC enforcement
```

### Dependencies

- **REQ-014**: Survey response persistence (provides call_attempts and transcript_snippets tables)
- **REQ-002**: OIDC authentication (provides `get_current_user` dependency)
- **REQ-003**: RBAC authorization (provides role-based access control)

### Data Flow

```
HTTP Request → Router → RBAC Check → Service → Repository → Database
                                         ↓
HTTP Response ← Router ← Service ← CallDetailResponse
```

## Key Components

### CallDetailResponse Model

```python
class CallDetailResponse(BaseModel):
    call_id: str
    contact_id: UUID
    campaign_id: UUID
    attempt_number: int  # >= 1
    provider_call_id: Optional[str]
    outcome: CallAttemptOutcome
    started_at: datetime
    answered_at: Optional[datetime]
    ended_at: Optional[datetime]
    error_code: Optional[str]
    provider_raw_status: Optional[str]
    transcript_snippet: Optional[TranscriptSnippet]
    recording_url: Optional[str]
```

### CallDetailService

The service layer handles:
1. Fetching call attempt by `call_id`
2. Verifying campaign access for the requesting user
3. Fetching associated transcript if available
4. Extracting recording URL from metadata if present

### RBAC Enforcement

Access is restricted to users with `campaign_manager` or `admin` roles:
- `viewer` role receives 403 Forbidden
- Unauthenticated requests receive 401 Unauthorized

## Testing

### Unit Tests

- `test_call_detail_service.py`: Tests business logic with fake repository
- `test_call_models.py`: Tests Pydantic model validation

### Integration Tests

- `test_call_detail_router.py`: Tests HTTP layer with dependency injection

### Running Tests

```bash
cd runs/kit/REQ-020
pytest -v test/
```

## API Documentation

### Endpoint

```
GET /api/calls/{call_id}
```

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| Authorization | Yes | Bearer token from OIDC |

### Response Codes

| Code | Description |
|------|-------------|
| 200 | Call details retrieved successfully |
| 401 | Not authenticated |
| 403 | Access denied (viewer role or campaign access) |
| 404 | Call not found |

### Example Response

```json
{
  "call_id": "call-abc123",
  "contact_id": "d4444444-4444-4444-4444-444444444444",
  "campaign_id": "c2222222-2222-2222-2222-222222222222",
  "attempt_number": 1,
  "provider_call_id": "CA1234567890abcdef",
  "outcome": "completed",
  "started_at": "2024-01-15T10:30:00Z",
  "answered_at": "2024-01-15T10:30:15Z",
  "ended_at": "2024-01-15T10:35:00Z",
  "error_code": null,
  "provider_raw_status": "completed",
  "transcript_snippet": {
    "text": "Hello, this is a survey call...",
    "language": "en",
    "created_at": "2024-01-15T10:35:01Z"
  },
  "recording_url": null
}
```

## Integration Notes

### Wiring Dependencies

In production, override the dependency stubs:

```python
from app.calls.router import get_current_user, get_call_detail_service

app.dependency_overrides[get_current_user] = your_auth_dependency
app.dependency_overrides[get_call_detail_service] = your_service_factory
```

### Database Requirements

Requires tables from REQ-001 migrations:
- `call_attempts` - stores call attempt records
- `transcript_snippets` - stores transcript data (optional)