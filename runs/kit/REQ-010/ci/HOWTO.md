# REQ-010: Telephony Webhook Handler - Execution Guide

## Overview

This KIT implements the telephony webhook handler for receiving and processing
provider callbacks. It parses events into domain CallEvent objects and updates
database state accordingly.

## Prerequisites

- Python 3.12+
- PostgreSQL 15+ (for integration tests)
- pip or poetry for dependency management

## Environment Setup

### Required Environment Variables

bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/voicesurvey"
export TWILIO_ACCOUNT_SID="your_account_sid"
export TWILIO_AUTH_TOKEN="your_auth_token"
export LOG_LEVEL="INFO"

### PYTHONPATH Configuration

The module depends on code from previous REQs. Set PYTHONPATH to include all
required source directories:

bash
export PYTHONPATH="runs/kit/REQ-010/src:runs/kit/REQ-009/src:runs/kit/REQ-008/src:runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

## Installation

bash
# Install dependencies
pip install -r runs/kit/REQ-010/requirements.txt

# Or with poetry
poetry install

## Running Tests

### Unit Tests

bash
# Run all tests
pytest runs/kit/REQ-010/test -v

# Run with coverage
pytest runs/kit/REQ-010/test -v --cov=app --cov-report=term-missing

# Run specific test file
pytest runs/kit/REQ-010/test/test_webhook_handler.py -v

### Linting

bash
# Check code style
ruff check runs/kit/REQ-010/src runs/kit/REQ-010/test

# Auto-fix issues
ruff check runs/kit/REQ-010/src runs/kit/REQ-010/test --fix

### Type Checking

bash
mypy runs/kit/REQ-010/src --ignore-missing-imports

## API Endpoints

### POST /webhooks/telephony/events

Receives webhook callbacks from the telephony provider.

**Request Format (Twilio):**
- Content-Type: application/x-www-form-urlencoded
- Query parameters: call_id, campaign_id, contact_id (passed via callback URL)

**Form Fields:**
- CallSid: Provider call identifier
- CallStatus: Call status (queued, ringing, in-progress, completed, etc.)
- CallDuration: Duration in seconds (for completed calls)
- ErrorCode: Error code (for failed calls)
- ErrorMessage: Error message (for failed calls)

**Response:**
json
{
  "status": "processed",
  "call_id": "test-call-123",
  "event_type": "call.answered"
}

## Event Types

| Twilio Status | Domain Event | Action |
|---------------|--------------|--------|
| queued | call.initiated | Log status |
| initiated | call.initiated | Log status |
| ringing | call.ringing | Log status |
| in-progress | call.answered | Trigger dialogue start |
| completed | call.completed | Record duration |
| no-answer | call.no_answer | Update contact state |
| busy | call.busy | Update contact state |
| failed | call.failed | Log error, update state |

## Idempotency

The handler implements idempotent processing via:
1. In-memory cache for same-request duplicates
2. Database tracking of processed events per call_id

Duplicate events return `{"status": "duplicate"}` without re-processing.

## Troubleshooting

### Import Errors

If you see import errors, ensure PYTHONPATH includes all required source directories:

bash
export PYTHONPATH="runs/kit/REQ-010/src:runs/kit/REQ-009/src:..."

### Database Connection

For tests, the mock session is used. For integration testing, ensure PostgreSQL
is running and DATABASE_URL is correctly configured.

### Signature Validation

Twilio signature validation requires:
- X-Twilio-Signature header
- Full request URL
- TWILIO_AUTH_TOKEN environment variable

In development, invalid signatures are logged but not rejected.

## Architecture

app/telephony/
├── __init__.py           # Module exports
├── events.py             # CallEvent domain model
├── interface.py          # TelephonyProvider interface
├── adapters/
│   ├── __init__.py
│   └── twilio.py         # Twilio adapter implementation
└── webhooks/
    ├── __init__.py
    ├── handler.py        # Event processing logic
    ├── router.py         # FastAPI router
    └── schemas.py        # Pydantic schemas

## Dependencies

This REQ depends on:
- REQ-001: Database schema (CallAttempt, Contact models)
- REQ-009: TelephonyProvider interface

This REQ is required by:
- REQ-012: Dialogue orchestrator consent flow