# KIT Documentation — REQ-016: Email Worker Service

## Overview

REQ-016 implements the email worker service that continuously polls an SQS queue for survey events and sends corresponding templated emails to contacts.

## Acceptance Criteria Coverage

| Criterion | Implementation | Status |
|-----------|----------------|--------|
| Email worker polls SQS queue continuously | `EmailWorker` with `SQSConsumer` using long-polling | ✅ |
| survey.completed triggers completed email if template configured | `EmailService.process_event()` checks campaign template config | ✅ |
| Template variables substituted from event payload | `TemplateRenderer` with `{{variable}}` syntax | ✅ |
| EmailNotification record created with status | `EmailRepository.create_notification()` | ✅ |
| Failed sends retried up to 3 times with backoff | `RetryPolicy` with exponential backoff | ✅ |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  SQS Queue  │────▶│ SQSConsumer  │────▶│ EmailWorker  │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                    ┌──────────────┐     ┌──────▼───────┐
                    │EmailProvider │◀────│ EmailService │
                    │   (SMTP)     │     └──────┬───────┘
                    └──────────────┘            │
                                         ┌──────▼───────┐
                                         │  Repository  │
                                         │  (Database)  │
                                         └──────────────┘
```

## Components

### EmailWorker
Main worker class that:
- Starts/stops the polling loop
- Processes events with retry logic
- Acknowledges messages after processing

### SQSConsumer
Async SQS message consumer that:
- Uses long-polling for efficiency
- Parses messages into domain events
- Handles message acknowledgment

### EmailService
Business logic for email processing:
- Idempotency check via event_id
- Template lookup based on event type
- Variable substitution and rendering
- Notification record management

### TemplateRenderer
Template engine supporting:
- `{{variable}}` syntax
- HTML escaping for security
- Missing variable handling

### SMTPEmailProvider
SMTP implementation of EmailProvider:
- TLS support
- Authentication
- Async operation via thread pool

## Configuration

Environment variables:
- `SQS_QUEUE_URL` - SQS queue URL (required)
- `AWS_REGION` - AWS region (default: eu-central-1)
- `SMTP_HOST` - SMTP server host
- `SMTP_PORT` - SMTP server port (default: 587)
- `SMTP_USERNAME` - SMTP authentication username
- `SMTP_PASSWORD` - SMTP authentication password
- `SMTP_USE_TLS` - Enable TLS (default: true)
- `EMAIL_FROM` - Default sender email
- `EMAIL_MAX_RETRIES` - Max retry attempts (default: 3)

## Event Types Handled

| Event Type | Template Type | Trigger |
|------------|---------------|---------|
| survey.completed | completed | Survey successfully completed |
| survey.refused | refused | Contact refused consent |
| survey.not_reached | not_reached | Max attempts exhausted |

## Dependencies

- REQ-015: Event publisher service (produces events)
- REQ-001: Database schema (email_notifications, email_templates tables)

## Testing

```bash
cd runs/kit/REQ-016
pip install -r requirements.txt
PYTHONPATH=src pytest test/ -v
```

## Error Handling

1. **Malformed messages**: Deleted from queue to prevent infinite retry
2. **Missing template**: Event acknowledged, no email sent
3. **Missing contact email**: Event acknowledged, no email sent
4. **SMTP failures**: Retried with exponential backoff up to max_retries
5. **Database errors**: Retried with backoff