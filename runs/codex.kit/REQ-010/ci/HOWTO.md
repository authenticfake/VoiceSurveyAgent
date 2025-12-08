# HOWTO — REQ-010 Workers & Messaging

## Prerequisites
- Python 3.12+
- AWS credentials with SQS permissions (or localstack/moto for tests)
- Boto3-compatible network access
- Optional: virtualenv (`python -m venv .venv && source .venv/bin/activate`)

Install dependencies:
```bash
pip install -r runs/kit/REQ-010/requirements.txt
```

## Environment Setup
Set mandatory config via env vars (examples):

```bash
export APP__DATABASE__URL=postgresql://user:pass@host/db
export APP__MESSAGING__QUEUE_URL=https://sqs.eu-central-1.amazonaws.com/123/survey-events.fifo
export APP__MESSAGING__REGION_NAME=eu-central-1
export APP__SCHEDULER__FACTORY_PATH=app.calling.scheduler.service:build_scheduler
export APP__EMAIL_WORKER__HANDLER_FACTORY_PATH=app.notifications.email.worker:build_handler
export PYTHONPATH=runs/kit/REQ-010/src
```

Optional overrides:
- `APP__MESSAGING__FIFO=true`
- `APP__EMAIL_WORKER__LONG_POLL_SECONDS=20`
- `APP__PROVIDER__OUTBOUND_NUMBER=+12065550100`

## Running Workers
Scheduler:
```bash
python -m app.workers.scheduler           # continuous
python -m app.workers.scheduler --once    # single cycle smoke test
```

Email worker:
```bash
python -m app.workers.email               # continuous poller
python -m app.workers.email --max-loops 1 # bounded loop (tests)
```

### Kubernetes/EKS
- Package workers as separate deployments.
- Mount env vars via ConfigMap/Secrets.
- Ensure IAM roles (IRSA) grant SQS permissions.

## Tests
```bash
PYTHONPATH=runs/kit/REQ-010/src pytest -q runs/kit/REQ-010/test
```
(Use same command as CI to collect coverage.)

## Troubleshooting
- **Import errors**: confirm `PYTHONPATH` includes `runs/kit/REQ-010/src`.
- **SQS auth failures**: verify AWS credentials or IAM roles.
- **Handler factory errors**: ensure import path format `module:callable` and callable returns object with required methods.
- **JSON logging**: logs print as single-line JSON; pipe through `jq` for readability.