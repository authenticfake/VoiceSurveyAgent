# KIT Documentation: REQ-010 - Telephony Webhook Handler

## Summary

REQ-010 implements the telephony webhook handler that receives provider callbacks
and processes them into domain events. The handler updates call attempt and
contact state based on event type, with idempotent processing to handle
duplicate webhook deliveries.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| POST /webhooks/telephony/events receives provider callbacks | ✅ | `webhooks/router.py` |
| Events parsed into domain CallEvent objects | ✅ | `adapters/twilio.py` |
| call.answered triggers dialogue start | ✅ | `webhooks/handler.py` |
| call.no_answer updates attempt outcome and contact state | ✅ | `webhooks/handler.py` |
| Duplicate events handled idempotently via call_id | ✅ | `webhooks/handler.py` |

## Components

### CallEvent Domain Model (`events.py`)

Normalized representation of telephony events:
- `event_type`: Enum of event types (INITIATED, RINGING, ANSWERED, etc.)
- `call_id`: Internal call identifier
- `provider_call_id`: Provider's unique identifier
- `campaign_id`, `contact_id`: UUIDs for context
- `timestamp`, `duration_seconds`, `error_code`, etc.

### TelephonyProvider Interface (`interface.py`)

Extended from REQ-009 with `parse_webhook_event` method:
- Parses provider-specific payload into CallEvent
- Validates webhook signature if supported
- Raises ValueError for invalid payloads

### TwilioAdapter (`adapters/twilio.py`)

Implements webhook parsing for Twilio:
- Maps Twilio status to domain event types
- Extracts metadata from query parameters
- Validates HMAC-SHA1 signatures

### WebhookHandler (`webhooks/handler.py`)

Core event processing logic:
- Idempotent processing via call_id + event_type
- Updates CallAttempt records
- Updates Contact state for terminal events
- Triggers dialogue start on call.answered

### Webhook Router (`webhooks/router.py`)

FastAPI endpoint:
- Receives form-encoded webhook data
- Parses query parameters for metadata
- Validates signature if present
- Returns processing status

## Event Flow

Provider Webhook → Router → Parse Event → Handler → Database Update
                                              ↓
                                    Dialogue Start (if answered)

## Idempotency Strategy

1. **In-memory cache**: Tracks processed events within request lifecycle
2. **Database tracking**: Stores processed event types in CallAttempt.metadata
3. **Duplicate detection**: Returns early without re-processing

## State Transitions

| Event | CallAttempt.outcome | Contact.state |
|-------|---------------------|---------------|
| call.answered | - | - |
| call.no_answer | NO_ANSWER | NOT_REACHED |
| call.busy | BUSY | NOT_REACHED |
| call.failed | FAILED | NOT_REACHED |
| call.completed | - | - |

Note: call.completed at telephony level doesn't set outcome; survey completion
is handled by dialogue orchestrator (REQ-014).

## Testing

- Unit tests for handler logic with mocked session
- Unit tests for Twilio adapter parsing
- Integration tests for router endpoint
- All tests use pytest-asyncio for async support

## Dependencies

- **REQ-001**: Database schema (CallAttempt, Contact models)
- **REQ-009**: TelephonyProvider interface definition

## Future Enhancements

- Support for additional telephony providers
- Webhook retry handling with exponential backoff
- Metrics for webhook processing latency
- Dead letter queue for failed events