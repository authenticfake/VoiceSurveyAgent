# REQ-008: Call Scheduler Service

## Overview

The call scheduler service is a background task that orchestrates outbound call attempts for voice survey campaigns. It runs periodically to select eligible contacts and initiate calls through the configured telephony provider.

## Features

- **Periodic Execution**: Runs every 60 seconds (configurable)
- **Smart Contact Selection**: Filters by state, attempt count, and exclusion flags
- **Time Window Enforcement**: Respects campaign call time restrictions
- **Concurrency Control**: Limits simultaneous calls
- **Failure Recovery**: Gracefully handles provider errors

## Quick Start

### Installation

```bash
pip install -r runs/kit/REQ-008/requirements.txt
```

### Configuration

Set environment variables:
```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"
```

### Usage

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.calls.scheduler import CallScheduler, CallSchedulerConfig

# Create scheduler
config = CallSchedulerConfig(
    interval_seconds=60,
    max_concurrent_calls=10,
    batch_size=50,
)
scheduler = CallScheduler(
    session=db_session,
    telephony_provider=provider,
    config=config,
)

# Start background task
await scheduler.start()

# Stop when done
await scheduler.stop()
```

## API Reference

### CallScheduler

Main scheduler class for call orchestration.

#### Methods

- `start()`: Start the background scheduler task
- `stop()`: Stop the scheduler
- `run_once()`: Execute a single scheduler iteration

### CallSchedulerConfig

Configuration dataclass for scheduler settings.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `interval_seconds` | int | 60 | Time between scheduler runs |
| `max_concurrent_calls` | int | 10 | Maximum simultaneous calls |
| `batch_size` | int | 50 | Contacts to process per campaign |

### CallAttemptRepository

Repository for call attempt database operations.

#### Methods

- `create(contact_id, campaign_id, attempt_number, call_id)`: Create attempt record
- `get_by_id(attempt_id)`: Get attempt by UUID
- `get_by_call_id(call_id)`: Get attempt by internal call ID
- `update_outcome(attempt_id, outcome, ...)`: Update attempt outcome
- `get_by_contact(contact_id, limit)`: Get attempts for a contact

## Testing

```bash
# Run all tests
pytest runs/kit/REQ-008/test -v

# Run with coverage
pytest runs/kit/REQ-008/test --cov=runs/kit/REQ-008/src
```

## Dependencies

- REQ-001: Database schema
- REQ-004: Campaign models
- REQ-005: Contact models
- REQ-006: Contact repository
- REQ-007: Exclusion list management
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-008**: Call scheduler service

### Rationale
REQ-008 depends on REQ-007 (Exclusion list management) which is marked as in_progress. The scheduler service is the next logical component in the call orchestration flow, building on the contact and campaign management established in previous REQs.

### In Scope
- Call scheduler background task implementation
- Contact selection logic (pending/not_reached states)
- Attempt count filtering (< max_attempts)
- Time window enforcement
- CallAttempt model and repository
- Contact state management (update to in_progress)
- Telephony provider protocol interface
- Comprehensive unit tests

### Out of Scope
- Actual telephony provider implementation (REQ-009)
- Webhook handling (REQ-010)
- Redis-based distributed locking (future enhancement)
- Retry interval enforcement (minimum time between attempts)

### How to Run Tests

```bash
# Set environment
export PYTHONPATH=runs/kit/REQ-008/src:runs/kit/REQ-007/src:runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test"

# Run migrations
psql -d voicesurvey_test -f runs/kit/REQ-001/src/storage/sql/V0001.up.sql

# Install dependencies
pip install -r runs/kit/REQ-008/requirements.txt

# Run tests
pytest runs/kit/REQ-008/test -v --tb=short
```

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ with test database
- All dependent REQ modules (REQ-001 through REQ-007)

### Dependencies and Mocks
- **MockTelephonyProvider**: Test double for telephony provider, allows testing call initiation without real provider
- **Database fixtures**: Create test campaigns, contacts with various states
- **No external services required**: Tests use mock provider and local database

### Product Owner Notes
- The scheduler implements a polling-based approach (every 60 seconds) as specified
- Concurrency is controlled via configuration, not distributed locking (single-instance assumption for slice-1)
- Time window checking uses simple time comparison; timezone handling may need enhancement for production
- Provider failures gracefully revert contact state to allow retry in next iteration

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql`: Schema for call_attempts table, contact states
- `runs/kit/REQ-005/src/app/campaigns/models.py`: Campaign model with max_attempts, time window fields
- `runs/kit/REQ-006/src/app/contacts/repository.py`: Contact repository patterns
- `runs/kit/REQ-007/src/app/contacts/exclusions/models.py`: Exclusion source patterns

```json
{
  "index": [
    {
      "req": "REQ-008",
      "src": [
        "runs/kit/REQ-008/src/app/calls/__init__.py",
        "runs/kit/REQ-008/src/app/calls/models.py",
        "runs/kit/REQ-008/src/app/calls/repository.py",
        "runs/kit/REQ-008/src/app/calls/scheduler.py",
        "runs/kit/REQ-008/src/app/contacts/models.py",
        "runs/kit/REQ-008/src/app/campaigns/models.py"
      ],
      "tests": [
        "runs/kit/REQ-008/test/test_scheduler.py",
        "runs/kit/REQ-008/test/conftest.py"
      ]
    }
  ]
}