# REQ-010 — Messaging & Worker Infra

## Overview
This package delivers the reusable infrastructure needed for survey event messaging and background workers:

- `app.infra.config`: strongly-typed environment loader (Pydantic) for DB, messaging, provider, scheduler, email worker, observability settings.
- `app.infra.messaging`: SQS publisher/consumer wrappers plus boto3 client factory.
- `app.infra.observability`: JSON logging setup for API + workers.
- `app.workers.scheduler` / `app.workers.email`: CLI entrypoints that load runtime implementations via configurable factories.

## Usage
1. Export environment variables (example):
   ```bash
   export APP__DATABASE__URL=postgresql://...
   export APP__MESSAGING__QUEUE_URL=https://sqs.eu-central-1.amazonaws.com/123/survey-events.fifo
   export APP__MESSAGING__REGION_NAME=eu-central-1
   export APP__SCHEDULER__FACTORY_PATH=app.calling.scheduler.service:build_scheduler
   export APP__EMAIL_WORKER__HANDLER_FACTORY_PATH=app.notifications.email.handlers:build_handler
   ```
2. Run workers:
   ```bash
   PYTHONPATH=runs/kit/REQ-010/src python -m app.workers.scheduler
   PYTHONPATH=runs/kit/REQ-010/src python -m app.workers.email
   ```

## Testing
Install dependencies via `pip install -r runs/kit/REQ-010/requirements.txt`, then run:
```bash
PYTHONPATH=runs/kit/REQ-010/src pytest -q runs/kit/REQ-010/test
```

## Extensibility
- Scheduler/email factories receive the full `AppSettings` object, enabling later REQs to wire DB sessions, repositories, etc.
- Messaging abstractions can support alternative brokers by implementing the same interface and exporting via config.