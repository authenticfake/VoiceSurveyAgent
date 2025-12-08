# REQ-006 — Event Bus & Email Worker

## Overview
This kit introduces the survey event publishing contract and the email notification worker that satisfies SPEC requirements for completed, refused, and not-reached calls. Components delivered:

- `app.events.bus` — canonical `SurveyEventMessage`, publisher, and exception handling.
- `app.infra.messaging.sqs` — composable SQS client and queue consumer adapter.
- `app.notifications.email` — SMTP provider, template renderer, notification processor, and worker loop.
- SQLAlchemy models for campaigns, contacts, events, templates, and notifications reused by processor logic.

## Running Tests
```bash
export PYTHONPATH=runs/kit/REQ-006/src
pip install -r runs/kit/REQ-006/requirements.txt
pytest -q runs/kit/REQ-006/test
```

## Worker Usage
Instantiate dependencies via your DI/container:

```python
from app.events.bus.publisher import EventPublisher
from app.infra.messaging.sqs import SQSQueueConfig, build_sqs_client, SQSQueueConsumer
from app.notifications.email.rendering import TemplateRenderer
from app.notifications.email.provider import SMTPEmailProvider
from app.notifications.email.service import EmailNotificationProcessor
from app.notifications.email.worker import SurveyEmailWorker
from sqlalchemy.orm import sessionmaker

queue_config = SQSQueueConfig(queue_url=<FIFO_URL>, region_name="eu-central-1")
sqs_client = build_sqs_client(queue_config)
consumer = SQSQueueConsumer(sqs_client, queue_config)
provider = SMTPEmailProvider(host="smtp.eu.mail", port=587, username="srv", password="secret")
renderer = TemplateRenderer()
session_factory = sessionmaker(...)
processor = EmailNotificationProcessor(session_factory, provider, renderer)
worker = SurveyEmailWorker(consumer, processor)
worker.run_forever()
```

## Configuration Inputs
- **SQS**: queue URL, region, long-poll settings (env-driven in higher layers).
- **SMTP**: host, port, credentials, and sender identity.
- **Database**: `session_factory` from existing SQLAlchemy engine binding.

## Observability
- Structured logs emitted at info/debug levels for publish/send flows.
- Failures leave the SQS receipt handle untouched so SQS retries according to visibility timeout.