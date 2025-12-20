# REQ-010: Telephony Webhook Handler

## Overview

This module implements the webhook handler for receiving and processing
telephony provider callbacks. It provides:

- FastAPI endpoint for receiving webhooks
- Event parsing from provider-specific format to domain model
- Idempotent event processing
- Database state updates for calls and contacts
- Integration point for dialogue orchestrator

## Quick Start

bash
# Set environment
export PYTHONPATH="runs/kit/REQ-010/src:runs/kit/REQ-009/src:..."
export DATABASE_URL="postgresql+asyncpg://..."

# Install dependencies
pip install -r runs/kit/REQ-010/requirements.txt

# Run tests
pytest runs/kit/REQ-010/test -v

## API

### POST /webhooks/telephony/events

Receives webhook callbacks from telephony provider.

**Query Parameters:**
- `call_id`: Internal call identifier
- `campaign_id`: Campaign UUID
- `contact_id`: Contact UUID

**Form Data (Twilio):**
- `CallSid`: Provider call ID
- `CallStatus`: Call status
- `CallDuration`: Duration (optional)
- `ErrorCode`: Error code (optional)

**Response:**
json
{
  "status": "processed",
  "call_id": "...",
  "event_type": "call.answered"
}

## Event Types

- `call.initiated` - Call queued/initiated
- `call.ringing` - Phone ringing
- `call.answered` - Call answered (triggers dialogue)
- `call.completed` - Call ended normally
- `call.no_answer` - No answer
- `call.busy` - Line busy
- `call.failed` - Call failed

## Architecture

webhooks/
├── router.py    # FastAPI endpoint
├── handler.py   # Event processing
└── schemas.py   # Request/response schemas

adapters/
└── twilio.py    # Twilio-specific parsing

events.py        # Domain event model
interface.py     # Provider interface

## See Also

- [KIT_REQ-010.md](KIT_REQ-010.md) - Detailed implementation documentation
- [HOWTO.md](../ci/HOWTO.md) - Execution guide

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-010**: Telephony webhook handler

### Rationale
REQ-010 depends on REQ-009 (Telephony provider adapter interface) which is marked as in_progress. This REQ implements the webhook endpoint and event processing logic that receives callbacks from the telephony provider and updates database state.

### In Scope
- POST /webhooks/telephony/events endpoint
- CallEvent domain model for normalized events
- Twilio adapter webhook parsing (parse_webhook_event method)
- WebhookHandler for processing events and updating state
- Idempotent event handling via call_id
- call.answered triggering dialogue start (via protocol)
- call.no_answer, call.busy, call.failed updating contact state
- Unit and integration tests

### Out of Scope
- Actual dialogue orchestrator implementation (REQ-012)
- Other telephony provider adapters
- Webhook retry/DLQ handling
- Metrics instrumentation

### How to Run Tests

bash
# Set PYTHONPATH to include all dependent REQ sources
export PYTHONPATH="runs/kit/REQ-010/src:runs/kit/REQ-009/src:runs/kit/REQ-008/src:runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install dependencies
pip install -r runs/kit/REQ-010/requirements.txt

# Run tests
pytest runs/kit/REQ-010/test -v --tb=short

# Run with coverage
pytest runs/kit/REQ-010/test -v --cov=app --cov-report=term-missing

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ (for integration tests with real DB)
- Environment variables: DATABASE_URL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

### Dependencies and Mocks
- **Database session**: Mocked with AsyncMock for unit tests
- **DialogueStarter**: Protocol-based, mocked in tests
- **TelephonyProvider**: Uses TwilioAdapter with test credentials
- **CallAttempt lookup**: Mocked to return test fixtures

### Product Owner Notes
- The webhook handler uses a protocol for DialogueStarterProtocol to allow future REQ-012 to inject the actual dialogue orchestrator
- Signature validation is logged but not enforced in development to support testing
- Event idempotency uses both in-memory cache and database tracking for robustness

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Database schema for call_attempts, contacts tables
- `runs/kit/REQ-009/src/app/telephony/interface.py` - TelephonyProvider interface (extended)
- `runs/kit/REQ-008/src/app/calls/models.py` - CallAttempt model reference
- `runs/kit/REQ-006/src/app/contacts/models.py` - Contact model with state enum
- `docs/harper/lane-guides/python.md` - Python lane testing requirements

json
{
  "index": [
    {
      "req": "REQ-010",
      "src": [
        "runs/kit/REQ-010/src/app/__init__.py",
        "runs/kit/REQ-010/src/app/telephony/__init__.py",
        "runs/kit/REQ-010/src/app/telephony/events.py",
        "runs/kit/REQ-010/src/app/telephony/interface.py",
        "runs/kit/REQ-010/src/app/telephony/adapters/__init__.py",
        "runs/kit/REQ-010/src/app/telephony/adapters/twilio.py",
        "runs/kit/REQ-010/src/app/telephony/webhooks/__init__.py",
        "runs/kit/REQ-010/src/app/telephony/webhooks/handler.py",
        "runs/kit/REQ-010/src/app/telephony/webhooks/router.py",
        "runs/kit/REQ-010/src/app/telephony/webhooks/schemas.py",
        "runs/kit/REQ-010/src/app/calls/__init__.py",
        "runs/kit/REQ-010/src/app/calls/models.py",
        "runs/kit/REQ-010/src/app/contacts/__init__.py",
        "runs/kit/REQ-010/src/app/contacts/models.py",
        "runs/kit/REQ-010/src/app/campaigns/__init__.py",
        "runs/kit/REQ-010/src/app/campaigns/models.py",
        "runs/kit/REQ-010/src/app/auth/__init__.py",
        "runs/kit/REQ-010/src/app/auth/models.py",
        "runs/kit/REQ-010/src/app/shared/__init__.py",
        "runs/kit/REQ-010/src/app/shared/logging.py",
        "runs/kit/REQ-010/src/app/shared/database.py"
      ],
      "tests": [
        "runs/kit/REQ-010/test/test_webhook_handler.py",
        "runs/kit/REQ-010/test/test_twilio_adapter.py",
        "runs/kit/REQ-010/test/test_webhook_router.py",
        "runs/kit/REQ-010/test/conftest.py"
      ]
    }
  ]
}