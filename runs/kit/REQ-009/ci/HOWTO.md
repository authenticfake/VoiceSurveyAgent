# REQ-009: Telephony Provider Adapter Interface - Execution Guide

## Overview

This KIT implements the telephony provider adapter interface for the VoiceSurveyAgent system. It provides:

- `TelephonyProvider` abstract interface defining `initiate_call` and `parse_webhook_event` methods
- `TwilioAdapter` concrete implementation for Twilio-compatible API
- `MockTelephonyAdapter` for testing without real telephony provider
- Configuration via environment variables and `ProviderConfig` entity

## Prerequisites

### Required Tools
- Python 3.12+
- pip or poetry for dependency management
- pytest for testing

### Environment Variables

```bash
# Provider selection (twilio or mock)
export TELEPHONY_PROVIDER_TYPE=mock

# Twilio credentials (required for twilio provider)
export TELEPHONY_TWILIO_ACCOUNT_SID=AC_your_account_sid
export TELEPHONY_TWILIO_AUTH_TOKEN=your_auth_token
export TELEPHONY_TWILIO_FROM_NUMBER=+14155550000

# Webhook configuration
export TELEPHONY_WEBHOOK_BASE_URL=https://your-domain.com
export TELEPHONY_MAX_CONCURRENT_CALLS=10
export TELEPHONY_CALL_TIMEOUT_SECONDS=60
```

## Local Development Setup

### 1. Install Dependencies

```bash
# From project root
pip install -r runs/kit/REQ-009/requirements.txt

# Or with poetry
poetry install
```

### 2. Set PYTHONPATH

```bash
# Include REQ-009 source and dependencies
export PYTHONPATH=runs/kit/REQ-009/src:runs/kit/REQ-001/src:runs/kit/REQ-002/src:$PYTHONPATH
```

### 3. Run Tests

```bash
# Run all tests with coverage
pytest runs/kit/REQ-009/test -v --cov=app.telephony --cov-report=term-missing

# Run specific test file
pytest runs/kit/REQ-009/test/test_twilio_adapter.py -v

# Run with verbose output
pytest runs/kit/REQ-009/test -v --tb=long
```

### 4. Run Linting

```bash
# Check code style
ruff check runs/kit/REQ-009/src runs/kit/REQ-009/test

# Auto-fix issues
ruff check runs/kit/REQ-009/src --fix
```

### 5. Run Type Checking

```bash
mypy runs/kit/REQ-009/src --ignore-missing-imports
```

## Usage Examples

### Using the Mock Adapter for Testing

```python
from app.telephony import MockTelephonyAdapter, CallInitiationRequest
from uuid import uuid4

# Create mock adapter
adapter = MockTelephonyAdapter()

# Create call request
request = CallInitiationRequest(
    to="+14155551234",
    from_number="+14155550000",
    callback_url="https://example.com/webhook",
    call_id="call-123",
    campaign_id=uuid4(),
    contact_id=uuid4(),
)

# Initiate call
response = await adapter.initiate_call(request)
print(f"Provider call ID: {response.provider_call_id}")

# Configure failure for testing error handling
adapter.configure_failure(
    should_fail=True,
    error_message="Test failure",
    error_code="TEST_ERROR",
)
```

### Using the Twilio Adapter

```python
from app.telephony import TwilioAdapter, get_telephony_provider
from app.telephony.config import TelephonyConfig, ProviderType

# Option 1: Use factory (recommended)
provider = get_telephony_provider()

# Option 2: Create directly with config
config = TelephonyConfig(
    provider_type=ProviderType.TWILIO,
    twilio_account_sid="AC_your_sid",
    twilio_auth_token="your_token",
    twilio_from_number="+14155550000",
)
adapter = TwilioAdapter(config=config)

# Initiate call
response = await adapter.initiate_call(request)
```

### Parsing Webhook Events

```python
# Twilio webhook payload (form data)
payload = {
    "CallSid": "CA123456",
    "CallStatus": "in-progress",
    "call_id": "call-123",
    "campaign_id": "uuid-string",
    "contact_id": "uuid-string",
}

event = adapter.parse_webhook_event(payload)
print(f"Event type: {event.event_type}")
print(f"Status: {event.status}")
```

## CI/CD Integration

### GitHub Actions

The LTC.json file defines test cases for CI:

```yaml
- name: Run REQ-009 Tests
  run: |
    pip install -r runs/kit/REQ-009/requirements.txt
    PYTHONPATH=runs/kit/REQ-009/src:runs/kit/REQ-001/src pytest runs/kit/REQ-009/test -v
```

### Jenkins Pipeline

```groovy
stage('REQ-009 Tests') {
    steps {
        sh 'pip install -r runs/kit/REQ-009/requirements.txt'
        sh 'PYTHONPATH=runs/kit/REQ-009/src pytest runs/kit/REQ-009/test --junitxml=reports/junit.xml'
    }
    post {
        always {
            junit 'reports/junit.xml'
        }
    }
}
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

```bash
# Ensure PYTHONPATH includes the src directory
export PYTHONPATH=runs/kit/REQ-009/src:$PYTHONPATH
```

### Twilio API Errors

Common error codes:
- `21211`: Invalid 'To' phone number
- `21214`: 'To' phone number cannot be reached
- `21215`: Account not authorized to call this number

### Mock Adapter Not Recording Calls

Ensure you're using the same adapter instance:

```python
# Use factory singleton
provider = get_telephony_provider()

# Or reset between tests
from app.telephony.factory import reset_provider
reset_provider()
```

## Architecture Notes

### Interface Design

The `TelephonyProvider` interface follows the Dependency Inversion Principle:
- High-level modules depend on the abstract interface
- Concrete adapters (Twilio, Mock) implement the interface
- Easy to swap providers without changing business logic

### Webhook Event Flow

1. Telephony provider sends webhook to `/webhooks/telephony/events`
2. Handler extracts payload and signature
3. Adapter validates signature (if configured)
4. Adapter parses payload into `WebhookEvent`
5. Event is processed by dialogue orchestrator (REQ-010)

### Configuration Hierarchy

1. Environment variables (highest priority)
2. `.env` file
3. Default values in `TelephonyConfig`