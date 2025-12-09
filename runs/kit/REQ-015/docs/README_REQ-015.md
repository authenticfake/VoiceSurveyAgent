# REQ-015: Event Publisher Service

## Overview

The Event Publisher Service provides a reliable mechanism for publishing survey events to AWS SQS. It enables event-driven architecture for the VoiceSurveyAgent system, allowing downstream services to react to survey outcomes.

## Features

- **EventPublisher Interface**: Clean abstraction for event publishing
- **SQS Implementation**: Production-ready AWS SQS adapter
- **Event Schemas**: Pydantic models for type-safe events
- **Message Deduplication**: Prevents duplicate processing via call_id
- **Retry with Backoff**: Handles transient failures gracefully
- **Async Support**: Both sync and async publishing methods

## Quick Start

```python
from app.events.service import create_event_service

# Create service
service = create_event_service(
    queue_url="https://sqs.eu-central-1.amazonaws.com/123/survey-events.fifo"
)

# Publish completed survey
service.publish_survey_completed(
    campaign_id="campaign-uuid",
    contact_id="contact-uuid",
    call_id="call-uuid",
    answers=["8", "Great service", "9"],
)
```

## Event Types

| Event Type | Description | Key Fields |
|------------|-------------|------------|
| `survey.completed` | Survey finished successfully | answers, confidence scores |
| `survey.refused` | Contact refused to participate | refusal_reason |
| `survey.not_reached` | Max attempts exhausted | total_attempts, last_outcome |

## Testing

```bash
# Install dependencies
pip install -r runs/kit/REQ-015/requirements.txt

# Run tests
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-015/src"
pytest runs/kit/REQ-015/test/ -v
```

## Documentation

- [KIT Documentation](./KIT_REQ-015.md) - Detailed implementation docs
- [Execution Guide](../ci/HOWTO.md) - How to run and test

## Related Requirements

- REQ-014: Survey response persistence
- REQ-016: Email worker service
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-015**: Event publisher service

### Rationale
REQ-015 depends on REQ-014 (Survey response persistence) which is marked as `in_progress`. This REQ implements the event publishing layer that enables downstream services (REQ-016 Email worker) to react to survey outcomes.

### In Scope
- `EventPublisher` interface with `publish` method
- `SQSEventPublisher` implementation for AWS SQS
- Event schemas: `SurveyCompletedEvent`, `SurveyRefusedEvent`, `SurveyNotReachedEvent`
- Message deduplication via `call_id`
- Exponential backoff retry on failures
- `InMemoryEventPublisher` for testing
- `EventService` high-level API
- Unit tests, integration tests with moto

### Out of Scope
- Actual SQS queue provisioning (infrastructure)
- Email worker implementation (REQ-016)
- Database persistence of events (handled by existing Event entity from REQ-001)

### How to Run Tests

```bash
# Set environment
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-015/src"
export AWS_ACCESS_KEY_ID=testing
export AWS_SECRET_ACCESS_KEY=testing
export AWS_DEFAULT_REGION=eu-central-1

# Install dependencies
pip install -r runs/kit/REQ-015/requirements.txt

# Run all tests
pytest runs/kit/REQ-015/test/ -v

# Run with coverage
pytest runs/kit/REQ-015/test/ -v --cov=runs/kit/REQ-015/src
```

### Prerequisites
- Python 3.12+
- pip
- For integration tests: moto[sqs] package
- For production: Valid AWS credentials with SQS permissions

### Dependencies and Mocks
- **boto3/botocore**: AWS SDK for SQS operations
- **moto**: Used in integration tests to mock AWS SQS
- **InMemoryEventPublisher**: Test double for unit tests without AWS

### Product Owner Notes
- Event schema follows SPEC data model for Event entity
- Message deduplication uses SHA256 hash of `{event_type}:{call_id}` for FIFO queues
- Standard queues supported but without deduplication
- Retry logic uses configurable exponential backoff (default: 3 retries, 1s base delay)

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql`: Referenced for Event entity schema and event_type enum
- `runs/kit/REQ-014/src/app/shared/__init__.py`: Module structure pattern
- `runs/kit/REQ-001/src/storage/seed/seed.sql`: Event payload structure examples

```json
{
  "index": [
    {
      "req": "REQ-015",
      "src": [
        "runs/kit/REQ-015/src/app/__init__.py",
        "runs/kit/REQ-015/src/app/shared/__init__.py",
        "runs/kit/REQ-015/src/app/events/__init__.py",
        "runs/kit/REQ-015/src/app/events/schemas.py",
        "runs/kit/REQ-015/src/app/events/publisher.py",
        "runs/kit/REQ-015/src/app/events/service.py"
      ],
      "tests": [
        "runs/kit/REQ-015/test/__init__.py",
        "runs/kit/REQ-015/test/test_event_schemas.py",
        "runs/kit/REQ-015/test/test_event_publisher.py",
        "runs/kit/REQ-015/test/test_event_service.py",
        "runs/kit/REQ-015/test/test_integration_events.py"
      ]
    }
  ]
}