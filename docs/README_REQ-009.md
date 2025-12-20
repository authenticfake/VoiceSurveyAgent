# REQ-009: Telephony Provider Adapter Interface

## Quick Start

```bash
# Install dependencies
pip install -r runs/kit/REQ-009/requirements.txt

# Set PYTHONPATH
export PYTHONPATH=runs/kit/REQ-009/src:runs/kit/REQ-001/src:$PYTHONPATH

# Run tests
pytest runs/kit/REQ-009/test -v
```

## What This Implements

- `TelephonyProvider` abstract interface for telephony operations
- `TwilioAdapter` for Twilio-compatible API
- `MockTelephonyAdapter` for testing
- Configuration via environment variables

## Key Files

| File | Purpose |
|------|---------|
| `src/app/telephony/interface.py` | Abstract interface and data classes |
| `src/app/telephony/twilio_adapter.py` | Twilio implementation |
| `src/app/telephony/mock_adapter.py` | Mock for testing |
| `src/app/telephony/factory.py` | Provider factory |

## Usage

```python
from app.telephony import get_telephony_provider, CallInitiationRequest
from uuid import uuid4

# Get provider (uses singleton pattern)
provider = get_telephony_provider()

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
response = await provider.initiate_call(request)
```

## Environment Variables

```bash
TELEPHONY_PROVIDER_TYPE=twilio  # or mock
TELEPHONY_TWILIO_ACCOUNT_SID=AC_xxx
TELEPHONY_TWILIO_AUTH_TOKEN=xxx
TELEPHONY_TWILIO_FROM_NUMBER=+14155550000
TELEPHONY_WEBHOOK_BASE_URL=https://your-domain.com
```

## See Also

- [Full Documentation](./KIT_REQ-009.md)
- [Execution Guide](../ci/HOWTO.md)
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-009**: Telephony provider adapter interface

### Rationale
REQ-009 is the next open REQ-ID with its dependency (REQ-001) already in_progress. This REQ establishes the telephony abstraction layer that will be used by REQ-010 (webhook handler) and REQ-008 (call scheduler).

### In Scope
- `TelephonyProvider` abstract interface with `initiate_call` and `parse_webhook_event` methods
- `TwilioAdapter` concrete implementation for Twilio-compatible API
- `MockTelephonyAdapter` for testing without real telephony provider
- Configuration via environment variables (`TelephonyConfig`)
- Factory function for provider instantiation with singleton pattern
- Comprehensive unit tests for all components
- LTC.json and HOWTO.md for CI/CD integration

### Out of Scope
- Actual webhook endpoint (REQ-010)
- Call scheduling logic (REQ-008)
- Database persistence of call attempts
- Real Twilio API integration testing (requires credentials)

### How to Run Tests

```bash
# Install dependencies
pip install -r runs/kit/REQ-009/requirements.txt

# Set PYTHONPATH to include source directories
export PYTHONPATH=runs/kit/REQ-009/src:runs/kit/REQ-001/src:runs/kit/REQ-002/src

# Run all tests with coverage
pytest runs/kit/REQ-009/test -v --cov=app.telephony --cov-report=term-missing

# Run specific test file
pytest runs/kit/REQ-009/test/test_twilio_adapter.py -v

# Run linting
ruff check runs/kit/REQ-009/src runs/kit/REQ-009/test

# Run type checking
mypy runs/kit/REQ-009/src --ignore-missing-imports
```

### Prerequisites
- Python 3.12+
- pytest >= 8.0
- httpx >= 0.27.0
- pydantic >= 2.7.0
- pydantic-settings >= 2.2.0
- ruff (for linting)
- mypy (for type checking)

### Dependencies and Mocks
- **httpx.AsyncClient**: Mocked in tests to avoid real HTTP calls to Twilio API
- **TelephonyConfig**: Uses environment variables with sensible defaults
- **MockTelephonyAdapter**: Provided for testing without real telephony provider

### Product Owner Notes
- The interface is designed for extensibility - adding new providers (e.g., Telnyx, Vonage) requires only implementing the `TelephonyProvider` interface
- Webhook signature validation is optional when auth token is not configured (useful for development)
- The mock adapter records all calls and webhooks for test assertions
- Metadata is passed through callback URLs as query parameters for correlation

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql`: Referenced for ProviderConfig entity schema (provider_type enum, provider_name, outbound_number, max_concurrent_calls)
- `runs/kit/REQ-002/src/app/auth/router.py`: Referenced for FastAPI router patterns
- `docs/harper/lane-guides/python.md`: Referenced for tool versions and testing patterns

### Index

```json
{
  "index": [
    {
      "req": "REQ-009",
      "src": [
        "runs/kit/REQ-009/src/app/__init__.py",
        "runs/kit/REQ-009/src/app/telephony/__init__.py",
        "runs/kit/REQ-009/src/app/telephony/interface.py",
        "runs/kit/REQ-009/src/app/telephony/config.py",
        "runs/kit/REQ-009/src/app/telephony/twilio_adapter.py",
        "runs/kit/REQ-009/src/app/telephony/mock_adapter.py",
        "runs/kit/REQ-009/src/app/telephony/factory.py"
      ],
      "tests": [
        "runs/kit/REQ-009/test/__init__.py",
        "runs/kit/REQ-009/test/test_interface.py",
        "runs/kit/REQ-009/test/test_twilio_adapter.py",
        "runs/kit/REQ-009/test/test_mock_adapter.py",
        "runs/kit/REQ-009/test/test_factory.py",
        "runs/kit/REQ-009/test/test_config.py"
      ]
    }
  ]
}