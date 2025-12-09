# REQ-015: Event Publisher Service - Execution Guide

## Overview

This KIT implements the Event Publisher Service for the VoiceSurveyAgent system. It provides:

- `EventPublisher` interface for publishing survey events
- `SQSEventPublisher` implementation for AWS SQS
- Event schemas for `survey.completed`, `survey.refused`, and `survey.not_reached`
- Message deduplication via `call_id`
- Exponential backoff retry on failures

## Prerequisites

### Required Tools

- Python 3.12+
- pip
- AWS credentials (for production) or moto (for testing)

### Dependencies

```bash
pip install -r runs/kit/REQ-015/requirements.txt
```

## Environment Setup

### For Testing (Local)

```bash
# Set PYTHONPATH to include source directory
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-015/src"

# Mock AWS credentials for moto
export AWS_ACCESS_KEY_ID=testing
export AWS_SECRET_ACCESS_KEY=testing
export AWS_DEFAULT_REGION=eu-central-1
```

### For Production

```bash
# Real AWS credentials via environment or IAM role
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
export AWS_DEFAULT_REGION=eu-central-1

# SQS Queue URL
export SQS_QUEUE_URL=https://sqs.eu-central-1.amazonaws.com/123456789/survey-events.fifo
```

## Running Tests

### All Tests

```bash
cd <project-root>
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-015/src"
pytest runs/kit/REQ-015/test/ -v
```

### Unit Tests Only

```bash
pytest runs/kit/REQ-015/test/test_event_schemas.py \
       runs/kit/REQ-015/test/test_event_publisher.py \
       runs/kit/REQ-015/test/test_event_service.py -v
```

### Integration Tests Only

```bash
pytest runs/kit/REQ-015/test/test_integration_events.py -v
```

### With Coverage

```bash
pytest runs/kit/REQ-015/test/ -v --cov=runs/kit/REQ-015/src --cov-report=html
```

### With JUnit Report

```bash
mkdir -p reports
pytest runs/kit/REQ-015/test/ -v --junitxml=reports/junit-req015.xml
```

## Usage Examples

### Creating an Event Service

```python
from app.events.service import create_event_service, EventService
from app.events.publisher import InMemoryEventPublisher

# For production with SQS
service = create_event_service(
    queue_url="https://sqs.eu-central-1.amazonaws.com/123/survey-events.fifo",
    region_name="eu-central-1",
    max_retries=3,
)

# For testing with in-memory publisher
publisher = InMemoryEventPublisher()
service = EventService(publisher)
```

### Publishing Events

```python
# Survey completed
service.publish_survey_completed(
    campaign_id="campaign-uuid",
    contact_id="contact-uuid",
    call_id="call-uuid",
    answers=["8", "Great service", "9"],
    attempts_count=1,
    q1_confidence=0.95,
)

# Survey refused
service.publish_survey_refused(
    campaign_id="campaign-uuid",
    contact_id="contact-uuid",
    call_id="call-uuid",
    refusal_reason="explicit_refusal",
)

# Survey not reached
service.publish_survey_not_reached(
    campaign_id="campaign-uuid",
    contact_id="contact-uuid",
    total_attempts=5,
    last_outcome="no_answer",
)
```

### Async Publishing

```python
import asyncio

async def publish_events():
    await service.publish_survey_completed_async(
        campaign_id="campaign-uuid",
        contact_id="contact-uuid",
        call_id="call-uuid",
        answers=["8", "Great service", "9"],
    )

asyncio.run(publish_events())
```

## Architecture

### Module Structure

```
runs/kit/REQ-015/src/app/events/
├── __init__.py          # Public exports
├── schemas.py           # Event data models (Pydantic)
├── publisher.py         # Publisher interface and implementations
└── service.py           # High-level event service
```

### Event Flow

1. Application calls `EventService.publish_survey_*()` method
2. Service creates appropriate event schema
3. Publisher serializes event to JSON
4. Publisher sends to SQS with message attributes
5. On failure, publisher retries with exponential backoff
6. Returns success/failure status

### Message Deduplication

- FIFO queues use `call_id` for deduplication
- Deduplication ID is SHA256 hash of `{event_type}:{call_id}`
- Message group ID is `campaign-{campaign_id}` for ordering

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

```bash
# Ensure PYTHONPATH includes the src directory
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-015/src"
```

### AWS Credential Errors

For testing, ensure moto mock credentials are set:

```bash
export AWS_ACCESS_KEY_ID=testing
export AWS_SECRET_ACCESS_KEY=testing
```

### SQS Connection Errors

For production, verify:
1. AWS credentials are valid
2. IAM role has `sqs:SendMessage` permission
3. Queue URL is correct
4. Network allows outbound HTTPS to SQS endpoint

### Test Failures

If integration tests fail:
1. Ensure `moto[sqs]` is installed
2. Check Python version is 3.12+
3. Run with `-v --tb=long` for detailed output

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run REQ-015 Tests
  env:
    PYTHONPATH: runs/kit/REQ-015/src
    AWS_ACCESS_KEY_ID: testing
    AWS_SECRET_ACCESS_KEY: testing
    AWS_DEFAULT_REGION: eu-central-1
  run: |
    pip install -r runs/kit/REQ-015/requirements.txt
    pytest runs/kit/REQ-015/test/ -v --junitxml=reports/junit-req015.xml
```

### Jenkins

```groovy
stage('REQ-015 Tests') {
    environment {
        PYTHONPATH = "${WORKSPACE}/runs/kit/REQ-015/src"
        AWS_ACCESS_KEY_ID = 'testing'
        AWS_SECRET_ACCESS_KEY = 'testing'
    }
    steps {
        sh 'pip install -r runs/kit/REQ-015/requirements.txt'
        sh 'pytest runs/kit/REQ-015/test/ -v --junitxml=reports/junit-req015.xml'
    }
}
```

## Related REQs

- **REQ-014**: Survey response persistence (provides data for events)
- **REQ-016**: Email worker service (consumes events from SQS)
- **REQ-012/013**: Dialogue orchestrator (triggers event publishing)