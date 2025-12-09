# HOWTO: REQ-016 Email Worker Service

## Prerequisites

- Python 3.12+
- pip
- Access to AWS SQS (or LocalStack for local testing)
- SMTP server (or MailHog for local testing)

## Environment Setup

### 1. Create Virtual Environment

```bash
cd runs/kit/REQ-016
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file or export variables:

```bash
# Required
export SQS_QUEUE_URL="https://sqs.eu-central-1.amazonaws.com/123456789/survey-events"

# AWS credentials (if not using IAM roles)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="eu-central-1"

# SMTP configuration
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-username"
export SMTP_PASSWORD="your-password"
export SMTP_USE_TLS="true"
export EMAIL_FROM="noreply@example.com"
export EMAIL_FROM_NAME="Voice Survey"

# Worker settings
export EMAIL_MAX_RETRIES="3"
export EMAIL_RETRY_BASE_DELAY="1.0"
export EMAIL_POLL_INTERVAL="5.0"
```

## Running Tests

### Unit Tests

```bash
cd runs/kit/REQ-016
PYTHONPATH=src pytest test/ -v
```

### With Coverage

```bash
PYTHONPATH=src pytest test/ -v --cov=app --cov-report=html
```

### Specific Test File

```bash
PYTHONPATH=src pytest test/test_email_service.py -v
```

## Local Development

### Using LocalStack for SQS

```bash
# Start LocalStack
docker run -d -p 4566:4566 localstack/localstack

# Create queue
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name survey-events

# Set environment
export SQS_QUEUE_URL="http://localhost:4566/000000000000/survey-events"
export AWS_ENDPOINT_URL="http://localhost:4566"
```

### Using MailHog for SMTP

```bash
# Start MailHog
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Set environment
export SMTP_HOST="localhost"
export SMTP_PORT="1025"
export SMTP_USE_TLS="false"
export SMTP_USERNAME=""
export SMTP_PASSWORD=""

# View emails at http://localhost:8025
```

## CI/CD Integration

### GitHub Actions

The LTC.json file defines test cases for CI:

```yaml
- name: Run REQ-016 Tests
  run: |
    cd runs/kit/REQ-016
    pip install -r requirements.txt
    PYTHONPATH=src pytest test/ -v --junitxml=reports/junit.xml
```

### Jenkins

```groovy
stage('REQ-016 Tests') {
    dir('runs/kit/REQ-016') {
        sh 'pip install -r requirements.txt'
        sh 'PYTHONPATH=src pytest test/ -v --junitxml=reports/junit.xml'
    }
}
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=runs/kit/REQ-016/src
# or
cd runs/kit/REQ-016 && PYTHONPATH=src pytest test/
```

### SQS Connection Issues

1. Verify AWS credentials are configured
2. Check queue URL is correct
3. Ensure IAM permissions include `sqs:ReceiveMessage`, `sqs:DeleteMessage`

### SMTP Connection Issues

1. Verify SMTP host and port
2. Check TLS settings match server requirements
3. Verify credentials if authentication is required

### Test Failures

1. Check all dependencies are installed: `pip install -r requirements.txt`
2. Verify Python version: `python --version` (should be 3.12+)
3. Run with verbose output: `pytest -vvs`

## Production Deployment

### EKS Deployment

1. Build container image with email worker
2. Configure secrets in AWS Secrets Manager
3. Deploy as Kubernetes Deployment with:
   - Resource limits
   - Health checks
   - Graceful shutdown handling

### Environment Variables for Production

```yaml
env:
  - name: SQS_QUEUE_URL
    valueFrom:
      secretKeyRef:
        name: survey-secrets
        key: sqs-queue-url
  - name: SMTP_PASSWORD
    valueFrom:
      secretKeyRef:
        name: survey-secrets
        key: smtp-password
```

## Monitoring

### Metrics to Watch

- `email_sent_total` - Total emails sent
- `email_failed_total` - Failed email attempts
- `sqs_messages_processed_total` - Messages processed
- `email_send_latency_seconds` - Email send latency

### Logs

Worker logs include:
- Event processing start/completion
- Retry attempts with delays
- Error details for failures
- Message acknowledgment status
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-016**: Email worker service

### Rationale
REQ-016 is the next open REQ-ID in the dependency chain. It depends on REQ-015 (Event publisher service) which is marked as in_progress. The email worker consumes events published by REQ-015 and sends templated emails based on survey outcomes.

### In Scope
- Email worker that polls SQS queue continuously
- Processing of survey.completed, survey.refused, survey.not_reached events
- Template variable substitution from event payload
- EmailNotification record creation with status tracking
- Retry logic with exponential backoff (up to 3 retries)
- SMTP email provider implementation
- SQS consumer with long-polling
- Idempotent event processing

### Out of Scope
- SES or other cloud email provider implementations (SMTP only for slice-1)
- Email template CRUD API (templates managed via database)
- Email delivery tracking/webhooks
- Bounce handling

### How to Run Tests

```bash
cd runs/kit/REQ-016
pip install -r requirements.txt
PYTHONPATH=src pytest test/ -v
```

Or using the LTC cases:
```bash
# Install dependencies
pip install -r runs/kit/REQ-016/requirements.txt

# Run tests
cd runs/kit/REQ-016 && PYTHONPATH=src pytest test/ -v --tb=short
```

### Prerequisites
- Python 3.12+
- pip
- For integration testing: LocalStack (SQS) and MailHog (SMTP)

### Dependencies and Mocks
- **SQS Consumer**: Mocked in tests using AsyncMock
- **SMTP Server**: Mocked using unittest.mock.patch on smtplib.SMTP
- **Database Repository**: Mocked with AsyncMock for all database operations
- **Email Provider**: Interface allows injection of mock provider for testing

### Product Owner Notes
- The email worker is designed for single-tenant deployment as per SPEC
- Template rendering supports HTML escaping to prevent XSS in email content
- Idempotency is ensured via event_id tracking in email_notifications table
- Failed emails are logged but acknowledged to prevent infinite retry loops
- The worker supports graceful shutdown for container orchestration

### RAG Citations
- `runs/kit/REQ-015/src/app/shared/__init__.py` - Referenced for shared module structure
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Referenced for email_notifications and email_templates table schema
- `runs/kit/REQ-001/src/storage/seed/seed.sql` - Referenced for email template seed data structure
- `plan.json` - Used for REQ-016 acceptance criteria and dependencies

```json
{
  "index": [
    {
      "req": "REQ-016",
      "src": [
        "runs/kit/REQ-016/src/app/__init__.py",
        "runs/kit/REQ-016/src/app/shared/__init__.py",
        "runs/kit/REQ-016/src/app/email/__init__.py",
        "runs/kit/REQ-016/src/app/email/interfaces.py",
        "runs/kit/REQ-016/src/app/email/config.py",
        "runs/kit/REQ-016/src/app/email/template_renderer.py",
        "runs/kit/REQ-016/src/app/email/smtp_provider.py",
        "runs/kit/REQ-016/src/app/email/sqs_consumer.py",
        "runs/kit/REQ-016/src/app/email/repository.py",
        "runs/kit/REQ-016/src/app/email/service.py",
        "runs/kit/REQ-016/src/app/email/worker.py",
        "runs/kit/REQ-016/src/app/email/factory.py"
      ],
      "tests": [
        "runs/kit/REQ-016/test/conftest.py",
        "runs/kit/REQ-016/test/test_template_renderer.py",
        "runs/kit/REQ-016/test/test_email_service.py",
        "runs/kit/REQ-016/test/test_worker.py",
        "runs/kit/REQ-016/test/test_sqs_consumer.py",
        "runs/kit/REQ-016/test/test_smtp_provider.py"
      ],
      "docs": [
        "runs/kit/REQ-016/docs/KIT_REQ-016.md",
        "runs/kit/REQ-016/docs/README_REQ-016.md"
      ],
      "ci": [
        "runs/kit/REQ-016/ci/LTC.json",
        "runs/kit/REQ-016/ci/HOWTO.md"
      ]
    }
  ]
}