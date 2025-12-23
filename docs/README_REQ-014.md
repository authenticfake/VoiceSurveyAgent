# REQ-014: Survey Response Persistence

## Summary

This module implements atomic persistence of survey responses for the VoiceSurveyAgent system. When a survey is completed, it creates a `SurveyResponse` record with all 3 answers, updates the `Contact` state to completed, and records the `CallAttempt` outcome—all within a single database transaction.

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL database with schema from REQ-001
- Environment variable `DATABASE_URL` set

### Installation

```bash
cd runs/kit/REQ-014
pip install -r requirements.txt
```

### Running Tests

```bash
# Unit tests (no database required)
pytest test/test_persistence.py -v

# Integration tests (requires database)
SKIP_INTEGRATION_TESTS=false pytest test/test_persistence_integration.py -v
```

## API Reference

### SurveyPersistenceService

Main service for persisting survey outcomes.

#### Methods

- `persist_completed_survey(session, dialogue_session)` → `PersistenceResult`
  - Atomically persists completed survey with all 3 answers
  - Updates contact state to `completed`
  - Updates call attempt outcome to `completed`

- `persist_refused_survey(session, dialogue_session)` → `PersistenceResult`
  - Updates contact state to `refused`
  - Updates call attempt outcome to `refused`

### PersistenceResult

Result object returned by persistence operations.

```python
@dataclass
class PersistenceResult:
    success: bool
    survey_response_id: UUID | None
    contact_id: UUID | None
    call_attempt_id: UUID | None
    error_message: str | None
    completed_at: datetime | None
```

## Database Schema

The module uses these tables from REQ-001:

- `survey_responses`: Stores completed survey answers
- `contacts`: Contact records with state tracking
- `call_attempts`: Call attempt records with outcomes

## Integration Points

- **Input**: `DialogueSession` from REQ-013 with captured answers
- **Output**: Persisted `SurveyResponse` and updated states
- **Events**: Ready for REQ-015 event publishing integration