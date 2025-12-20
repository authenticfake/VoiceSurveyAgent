# KIT Documentation - REQ-008: Call Scheduler Service

## Summary

REQ-008 implements the call scheduler service that orchestrates outbound call attempts for voice survey campaigns. The scheduler runs as a background task, selecting eligible contacts and initiating calls through the telephony provider.

## Acceptance Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| Scheduler runs as background task every 60 seconds | ✅ Implemented | Configurable interval via `CallSchedulerConfig` |
| Selects contacts with state pending or not_reached | ✅ Implemented | Query filters in `_get_eligible_contacts` |
| Filters by attempts_count < campaign.max_attempts | ✅ Implemented | Query filter ensures retry limit |
| Filters by current time within allowed_call_start/end window | ✅ Implemented | `_is_within_call_window` method |
| Creates CallAttempt record before initiating call | ✅ Implemented | Record created before provider call |

## Implementation Details

### Components

#### CallScheduler (`app/calls/scheduler.py`)
Main scheduler service with:
- Background task loop with configurable interval
- Campaign and contact selection logic
- Call initiation with telephony provider
- Error handling and state management

#### CallAttemptRepository (`app/calls/repository.py`)
Database operations for call attempts:
- Create new attempt records
- Query by ID or call_id
- Update outcomes
- Get attempts by contact

#### CallAttempt Model (`app/calls/models.py`)
SQLAlchemy model matching REQ-001 schema:
- UUID primary key
- Foreign keys to contacts and campaigns
- Outcome enum (completed, refused, no_answer, busy, failed)
- Timestamps and metadata

### Configuration

```python
@dataclass
class CallSchedulerConfig:
    interval_seconds: int = 60      # Scheduler run interval
    max_concurrent_calls: int = 10  # Concurrency limit
    batch_size: int = 50            # Contacts per iteration
```

### Contact Selection Criteria

Contacts are eligible for calling when:
1. `state` is `pending` or `not_reached`
2. `attempts_count` < campaign's `max_attempts`
3. `do_not_call` is `False`
4. Current time is within campaign's call window

### Call Flow

1. Scheduler iteration starts
2. Query running campaigns
3. For each campaign:
   - Check time window
   - Get eligible contacts
   - For each contact:
     - Update state to `in_progress`
     - Increment `attempts_count`
     - Create `CallAttempt` record
     - Initiate call via provider
4. Commit transaction
5. Wait for next interval

### Error Handling

- Provider failures revert contact state to `pending`
- Exceptions are logged with correlation IDs
- Scheduler continues after individual call failures

## Dependencies

| REQ | Dependency Type | Description |
|-----|-----------------|-------------|
| REQ-001 | Schema | call_attempts table, contact state enum |
| REQ-004 | Model | Campaign model with max_attempts, time window |
| REQ-005 | Model | Contact model with state management |
| REQ-006 | Repository | Contact query patterns |
| REQ-007 | Logic | do_not_call exclusion flag |

## Testing

### Test Coverage

- Pending contact selection
- Not-reached contact retry
- Do-not-call exclusion
- Max attempts exclusion
- Call attempt record creation
- Contact state updates
- Concurrency limits
- Campaign status filtering
- Time window filtering
- Provider failure handling

### Running Tests

```bash
PYTHONPATH=runs/kit/REQ-008/src:... pytest runs/kit/REQ-008/test -v
```

## Future Enhancements

- Redis-based distributed locking for multi-instance deployment
- Retry interval enforcement (minimum time between attempts)
- Provider rate limiting integration
- Metrics and observability hooks