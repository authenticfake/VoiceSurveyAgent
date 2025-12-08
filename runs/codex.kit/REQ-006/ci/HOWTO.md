# HOWTO — Execute REQ-006 Assets

## Prerequisites
- Python 3.12+
- Access to an SQS queue (FIFO recommended) and SMTP server for end-to-end tests.
- Network access to AWS APIs if using real SQS.
- Environment variable `PYTHONPATH` must include `runs/kit/REQ-006/src`.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r runs/kit/REQ-006/requirements.txt
export PYTHONPATH=runs/kit/REQ-006/src
```

## Running Automated Tests
```bash
PYTHONPATH=runs/kit/REQ-006/src pytest -q runs/kit/REQ-006/test
```

## Local Worker Execution
1. Configure environment variables for SQS and SMTP (example):
   ```bash
   export SURVEY_EVENTS_QUEUE_URL="https://sqs.eu-central-1.amazonaws.com/123/voice-events.fifo"
   export AWS_REGION="eu-central-1"
   export SMTP_HOST="smtp.mail.eu"
   export SMTP_PORT="587"
   export SMTP_USERNAME="svc"
   export SMTP_PASSWORD="secret"
   ```
2. Inside a Python shell or script, wire dependencies (see README example) and call `SurveyEmailWorker.run_forever()`.

## Enterprise Runner Notes
- Jenkins/GitHub Actions: install dependencies via the provided `requirements.txt`, set `PYTHONPATH`, then invoke the LTC test command.
- Metrics/logs: the worker uses standard logging; route stdout/stderr to your log aggregation stack.
- For on-prem SMTP with self-signed certs, adjust `SMTPEmailProvider` to pass a custom SSL context.

## Troubleshooting
- **Import errors**: ensure `PYTHONPATH` includes `runs/kit/REQ-006/src`.
- **SQS permissions**: the IAM role must allow `sqs:SendMessage`, `ReceiveMessage`, and `DeleteMessage`.
- **SMTP auth failures**: verify credentials; enable application passwords if MFA-protected accounts are used.
- **SQLite missing JSONB**: tests use SQLite with SQLAlchemy JSON fallback; no additional action required.