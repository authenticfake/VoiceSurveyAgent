# KIT Documentation — REQ-014: Survey Response Persistence

## Overview

REQ-014 implements the survey response persistence layer for the VoiceSurveyAgent system. This component is responsible for atomically persisting completed survey responses, updating contact states, and recording call attempt outcomes within a single database transaction.

## Acceptance Criteria Coverage

| Criterion | Implementation | Status |
|-----------|----------------|--------|
| SurveyResponse created with all 3 answers | `SurveyResponseRepository.create_survey_response()` validates 3 answers and creates record | ✅ |
| Response linked to successful CallAttempt | `call_attempt_id` foreign key in SurveyResponse model | ✅ |
| Contact state updated to completed | `ContactRepository.update_state()` with `ContactState.COMPLETED` | ✅ |
| Timestamps recorded for completion | `completed_at` field set during persistence | ✅ |
| Transaction ensures atomicity of all updates | `SurveyPersistenceService.persist_completed_survey()` uses single session | ✅ |

## Architecture

### Module Structure

```
runs/kit/REQ-014/src/app/
├── __init__.py
├── shared/
│   ├── __init__.py
│   ├── logging.py
│   └── database.py
└── dialogue/
    ├── __init__.py
    ├── models.py              # Domain models (DialogueSession, CapturedAnswer)
    ├── persistence.py         # Persistence service and repositories
    └── persistence_models.py  # SQLAlchemy ORM models
```

### Key Components

1. **SurveyPersistenceService**: Main service orchestrating atomic persistence
2. **SurveyResponseRepository**: Repository for survey response CRUD
3. **ContactRepository**: Repository for contact state updates
4. **CallAttemptRepository**: Repository for call attempt outcome updates

### Domain Models

- `DialogueSession`: Represents an active dialogue with captured answers
- `CapturedAnswer`: Individual answer with confidence score
- `SurveyResponse`: Persisted survey response entity
- `Contact`: Contact entity with state tracking
- `CallAttempt`: Call attempt entity with outcome

## Usage

### Persisting a Completed Survey

```python
from app.dialogue.persistence import SurveyPersistenceService
from app.shared.database import get_db_context

service = SurveyPersistenceService()

async with get_db_context() as session:
    result = await service.persist_completed_survey(
        session=session,
        dialogue_session=completed_dialogue_session,
    )
    
    if result.success:
        print(f"Survey saved: {result.survey_response_id}")
    else:
        print(f"Error: {result.error_message}")
```

### Persisting a Refused Survey

```python
result = await service.persist_refused_survey(
    session=session,
    dialogue_session=refused_dialogue_session,
)
```

## Transaction Guarantees

The persistence service ensures:

1. **Atomicity**: All updates (survey response, contact state, call attempt outcome) succeed or fail together
2. **Idempotency**: Duplicate persistence attempts return existing response
3. **Validation**: Verifies contact and call attempt exist before persisting
4. **Error Handling**: Raises specific exceptions for different failure modes

## Dependencies

- REQ-001: Database schema (tables: contacts, call_attempts, survey_responses)
- REQ-013: Dialogue orchestrator Q&A flow (provides DialogueSession with answers)

## Testing

Run unit tests:
```bash
cd runs/kit/REQ-014
pytest test/ -v
```

Run with coverage:
```bash
pytest test/ -v --cov=src/app --cov-report=term-missing
```

## Error Handling

| Exception | Cause | Recovery |
|-----------|-------|----------|
| `NotFoundError` | Contact or CallAttempt not found | Verify IDs before calling |
| `TransactionError` | Database operation failed | Retry with backoff |
| `ValueError` | Invalid answer count | Ensure 3 answers captured |