# KIT Documentation: REQ-015 - Event Publisher Service

## Summary

REQ-015 implements the Event Publisher Service for the VoiceSurveyAgent system. This service provides a clean interface for publishing survey events to an SQS queue, enabling downstream consumers (like the email worker in REQ-016) to react to survey outcomes.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| EventPublisher interface defines publish method | ✅ | `EventPublisher` Protocol in `publisher.py` |
| SQS adapter implements publish to configured queue | ✅ | `SQSEventPublisher` class in `publisher.py` |
| Event schema includes event_type, campaign_id, contact_id, call_id | ✅ | `SurveyEvent` and subclasses in `schemas.py` |
| Message deduplication via call_id | ✅ | `_generate_deduplication_id()` method |
| Failed publishes retried with exponential backoff | ✅ | Retry loop in `publish()` method |

## Architecture

### Components

1. **Event Schemas** (`schemas.py`)
   - `SurveyEvent`: Base event with common fields
   - `SurveyCompletedEvent`: Survey completed with answers
   - `SurveyRefusedEvent`: Contact refused survey
   - `SurveyNotReachedEvent`: Contact not reached after max attempts

2. **Publisher Interface** (`publisher.py`)
   - `EventPublisher`: Protocol defining publish interface
   - `SQSEventPublisher`: Production implementation
   - `InMemoryEventPublisher`: Test implementation

3. **Event Service** (`service.py`)
   - High-level API for publishing events
   - Handles data transformation
   - Provides both sync and async methods

### Event Schema

```json
{
  "event_id": "uuid",
  "event_type": "survey.completed|survey.refused|survey.not_reached",
  "campaign_id": "uuid",
  "contact_id": "uuid",
  "call_id": "uuid|null",
  "timestamp": "ISO8601",
  "attempts_count": 1,
  // Type-specific fields...
}
```

### Message Attributes

SQS messages include these attributes for filtering:
- `event_type`: Event type string
- `campaign_id`: Campaign UUID
- `contact_id`: Contact UUID
- `call_id`: Call attempt UUID (if available)

## Dependencies

### Upstream (Required)
- REQ-014: Survey response persistence (provides survey data)
- REQ-001: Database schema (event storage)

### Downstream (Consumers)
- REQ-016: Email worker service (consumes events)

## Testing

### Test Coverage

- Unit tests for event schemas
- Unit tests for publisher implementations
- Integration tests with mocked SQS (moto)
- Async publishing tests

### Running Tests

```bash
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-015/src"
pytest runs/kit/REQ-015/test/ -v
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SQS_QUEUE_URL` | SQS queue URL | Required |
| `AWS_DEFAULT_REGION` | AWS region | `eu-central-1` |
| `EVENT_MAX_RETRIES` | Max retry attempts | `3` |

### FIFO vs Standard Queues

- FIFO queues (`.fifo` suffix): Include deduplication ID and message group ID
- Standard queues: No deduplication, higher throughput

## Error Handling

### Retry Strategy

1. On `ClientError`, wait with exponential backoff
2. Retry up to `max_retries` times
3. Log each failure with correlation ID
4. Return `False` if all retries exhausted

### Backoff Calculation

```python
delay = base_delay * (2 ** attempt)
delay = min(delay, max_delay)
```

## Integration Points

### With Dialogue Orchestrator (REQ-012/013)

```python
# After survey completion
event_service.publish_survey_completed(
    campaign_id=campaign.id,
    contact_id=contact.id,
    call_id=call_attempt.id,
    answers=survey_response.answers,
)
```

### With Email Worker (REQ-016)

Email worker polls SQS queue and processes events:
- `survey.completed` → Send thank you email
- `survey.refused` → Send refusal acknowledgment
- `survey.not_reached` → Send "we missed you" email