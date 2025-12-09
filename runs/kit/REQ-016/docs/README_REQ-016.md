# REQ-016: Email Worker Service

## Summary

This module implements the email worker service for the VoiceSurveyAgent platform. It continuously polls an SQS queue for survey events and sends templated emails to contacts based on survey outcomes.

## Features

- **Continuous SQS Polling**: Long-polling for efficient message consumption
- **Event-Driven Emails**: Sends emails based on survey.completed, survey.refused, and survey.not_reached events
- **Template Rendering**: Variable substitution with `{{variable}}` syntax
- **Retry Logic**: Exponential backoff for failed sends (up to 3 retries)
- **Idempotency**: Prevents duplicate emails via event_id tracking
- **Async Operations**: Non-blocking SMTP operations

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SQS_QUEUE_URL="https://sqs.eu-central-1.amazonaws.com/123456789/survey-events"
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USERNAME="user"
export SMTP_PASSWORD="secret"
export EMAIL_FROM="noreply@example.com"

# Run tests
PYTHONPATH=src pytest test/ -v
```

## Module Structure

```
src/app/email/
├── __init__.py          # Module exports
├── interfaces.py        # EmailProvider interface and data types
├── config.py            # Configuration classes
├── template_renderer.py # Template variable substitution
├── smtp_provider.py     # SMTP email provider implementation
├── sqs_consumer.py      # SQS message consumer
├── repository.py        # Database operations
├── service.py           # Email processing business logic
├── worker.py            # Main worker with retry logic
└── factory.py           # Component factory
```

## Usage

```python
from app.email.factory import create_email_worker
from app.email.config import EmailConfig, SQSConfig

# Create configuration
email_config = EmailConfig()
sqs_config = SQSConfig.from_env()

# Create and start worker
worker = create_email_worker(email_config, sqs_config, session_factory)
await worker.start()

# ... worker runs continuously ...

# Stop gracefully
await worker.stop()
```

## Template Variables

Available variables in email templates:

| Variable | Description | Available In |
|----------|-------------|--------------|
| `{{campaign_name}}` | Campaign name | All events |
| `{{contact_email}}` | Contact's email | All events |
| `{{answer_1}}` | First survey answer | completed |
| `{{answer_2}}` | Second survey answer | completed |
| `{{answer_3}}` | Third survey answer | completed |
| `{{attempts}}` | Number of call attempts | All events |

## Integration Points

- **Upstream**: REQ-015 Event Publisher (produces SQS messages)
- **Database**: Uses email_notifications and email_templates tables from REQ-001
- **External**: SMTP server for email delivery