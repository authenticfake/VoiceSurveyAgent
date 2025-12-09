"""
Unit tests for Twilio adapter.

REQ-010: Telephony webhook handler
"""

from uuid import uuid4

import pytest

from app.telephony.adapters.twilio import TwilioAdapter
from app.telephony.events import CallEventType

class TestTwilioAdapter:
    """Tests for TwilioAdapter."""

    @pytest.fixture
    def adapter(self) -> TwilioAdapter:
        """Create Twilio adapter for testing."""
        return TwilioAdapter(
            account_sid="test_sid",
            auth_token="test_token",
        )

    def test_parse_webhook_event_answered(self, adapter: TwilioAdapter) -> None:
        """Test parsing call.answered webhook."""
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = {
            "CallSid": "CA123456",
            "CallStatus": "in-progress",
            "From": "+14155551234",
            "To": "+14155555678",
            "Direction": "outbound-api",
            "call_id": "test-call-123",
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
        }

        event = adapter.parse_webhook_event(payload)

        assert event.event_type == CallEventType.ANSWERED
        assert event.call_id == "test-call-123"
        assert event.provider_call_id == "CA123456"
        assert event.campaign_id == campaign_id
        assert event.contact_id == contact_id
        assert event.raw_status == "in-progress"

    def test_parse_webhook_event_no_answer(self, adapter: TwilioAdapter) -> None:
        """Test parsing call.no_answer webhook."""
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = {
            "CallSid": "CA123456",
            "CallStatus": "no-answer",
            "call_id": "test-call-123",
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
        }

        event = adapter.parse_webhook_event(payload)

        assert event.event_type == CallEventType.NO_ANSWER
        assert event.raw_status == "no-answer"

    def test_parse_webhook_event_busy(self, adapter: TwilioAdapter) -> None:
        """Test parsing call.busy webhook."""
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = {
            "CallSid": "CA123456",
            "CallStatus": "busy",
            "call_id": "test-call-123",
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
        }

        event = adapter.parse_webhook_event(payload)

        assert event.event_type == CallEventType.BUSY

    def test_parse_webhook_event_completed(self, adapter: TwilioAdapter) -> None:
        """Test parsing call.completed webhook."""
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = {
            "CallSid": "CA123456",
            "CallStatus": "completed",
            "CallDuration": "120",
            "call_id": "test-call-123",
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
        }

        event = adapter.parse_webhook_event(payload)

        assert event.event_type == CallEventType.COMPLETED
        assert event.duration_seconds == 120

    def test_parse_webhook_event_failed(self, adapter: TwilioAdapter) -> None:
        """Test parsing call.failed webhook."""
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = {
            "CallSid": "CA123456",
            "CallStatus": "failed",
            "ErrorCode": "30003",
            "ErrorMessage": "Call rejected",
            "call_id": "test-call-123",
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
        }

        event = adapter.parse_webhook_event(payload)

        assert event.event_type == CallEventType.FAILED
        assert event.error_code == "30003"
        assert event.error_message == "Call rejected"

    def test_parse_webhook_event_missing_call_sid(
        self, adapter: TwilioAdapter
    ) -> None:
        """Test that missing CallSid raises ValueError."""
        payload = {
            "CallStatus": "in-progress",
            "call_id": "test-call-123",
            "campaign_id": str(uuid4()),
            "contact_id": str(uuid4()),
        }

        with pytest.raises(ValueError, match="Missing CallSid"):
            adapter.parse_webhook_event(payload)

    def test_parse_webhook_event_missing_metadata(
        self, adapter: TwilioAdapter
    ) -> None:
        """Test that missing metadata raises ValueError."""
        payload = {
            "CallSid": "CA123456",
            "CallStatus": "in-progress",
        }

        with pytest.raises(ValueError, match="Missing required metadata"):
            adapter.parse_webhook_event(payload)

    def test_parse_webhook_event_invalid_uuid(self, adapter: TwilioAdapter) -> None:
        """Test that invalid UUID raises ValueError."""
        payload = {
            "CallSid": "CA123456",
            "CallStatus": "in-progress",
            "call_id": "test-call-123",
            "campaign_id": "not-a-uuid",
            "contact_id": str(uuid4()),
        }

        with pytest.raises(ValueError, match="Invalid UUID"):
            adapter.parse_webhook_event(payload)

    def test_parse_webhook_event_unknown_status(
        self, adapter: TwilioAdapter
    ) -> None:
        """Test that unknown status defaults to FAILED."""
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = {
            "CallSid": "CA123456",
            "CallStatus": "unknown-status",
            "call_id": "test-call-123",
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
        }

        event = adapter.parse_webhook_event(payload)

        assert event.event_type == CallEventType.FAILED