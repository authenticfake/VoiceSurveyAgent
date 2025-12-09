"""
Tests for telephony provider interface.

REQ-009: Telephony provider adapter interface
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.telephony.interface import (
    CallInitiationRequest,
    CallInitiationResponse,
    CallInitiationError,
    CallStatus,
    TelephonyProvider,
    TelephonyProviderError,
    WebhookEvent,
    WebhookEventType,
    WebhookParseError,
)


class TestCallInitiationRequest:
    """Tests for CallInitiationRequest dataclass."""

    def test_create_request_with_required_fields(self) -> None:
        """Test creating request with required fields only."""
        campaign_id = uuid4()
        contact_id = uuid4()

        request = CallInitiationRequest(
            to="+14155551234",
            from_number="+14155550000",
            callback_url="https://example.com/webhook",
            call_id="call-123",
            campaign_id=campaign_id,
            contact_id=contact_id,
        )

        assert request.to == "+14155551234"
        assert request.from_number == "+14155550000"
        assert request.callback_url == "https://example.com/webhook"
        assert request.call_id == "call-123"
        assert request.campaign_id == campaign_id
        assert request.contact_id == contact_id
        assert request.language == "en"  # default
        assert request.metadata == {}  # default

    def test_create_request_with_all_fields(self) -> None:
        """Test creating request with all fields."""
        campaign_id = uuid4()
        contact_id = uuid4()
        metadata = {"custom_field": "value"}

        request = CallInitiationRequest(
            to="+393331234567",
            from_number="+393330000000",
            callback_url="https://example.com/webhook",
            call_id="call-456",
            campaign_id=campaign_id,
            contact_id=contact_id,
            language="it",
            metadata=metadata,
        )

        assert request.language == "it"
        assert request.metadata == metadata

    def test_request_is_immutable(self) -> None:
        """Test that request is frozen/immutable."""
        request = CallInitiationRequest(
            to="+14155551234",
            from_number="+14155550000",
            callback_url="https://example.com/webhook",
            call_id="call-123",
            campaign_id=uuid4(),
            contact_id=uuid4(),
        )

        with pytest.raises(AttributeError):
            request.to = "+14155559999"  # type: ignore


class TestCallInitiationResponse:
    """Tests for CallInitiationResponse dataclass."""

    def test_create_response(self) -> None:
        """Test creating response."""
        now = datetime.now(timezone.utc)

        response = CallInitiationResponse(
            provider_call_id="CA123456",
            status=CallStatus.QUEUED,
            created_at=now,
        )

        assert response.provider_call_id == "CA123456"
        assert response.status == CallStatus.QUEUED
        assert response.created_at == now
        assert response.raw_response == {}

    def test_create_response_with_raw_response(self) -> None:
        """Test creating response with raw provider response."""
        raw = {"sid": "CA123456", "status": "queued"}

        response = CallInitiationResponse(
            provider_call_id="CA123456",
            status=CallStatus.QUEUED,
            created_at=datetime.now(timezone.utc),
            raw_response=raw,
        )

        assert response.raw_response == raw


class TestWebhookEvent:
    """Tests for WebhookEvent dataclass."""

    def test_create_event_minimal(self) -> None:
        """Test creating event with minimal fields."""
        now = datetime.now(timezone.utc)

        event = WebhookEvent(
            event_type=WebhookEventType.CALL_ANSWERED,
            provider_call_id="CA123456",
            call_id=None,
            campaign_id=None,
            contact_id=None,
            status=CallStatus.IN_PROGRESS,
            timestamp=now,
        )

        assert event.event_type == WebhookEventType.CALL_ANSWERED
        assert event.provider_call_id == "CA123456"
        assert event.call_id is None
        assert event.campaign_id is None
        assert event.contact_id is None
        assert event.status == CallStatus.IN_PROGRESS
        assert event.timestamp == now
        assert event.duration_seconds is None
        assert event.error_code is None
        assert event.error_message is None

    def test_create_event_completed_with_duration(self) -> None:
        """Test creating completed event with duration."""
        campaign_id = uuid4()
        contact_id = uuid4()

        event = WebhookEvent(
            event_type=WebhookEventType.CALL_COMPLETED,
            provider_call_id="CA123456",
            call_id="call-123",
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=CallStatus.COMPLETED,
            timestamp=datetime.now(timezone.utc),
            duration_seconds=180,
        )

        assert event.duration_seconds == 180
        assert event.campaign_id == campaign_id
        assert event.contact_id == contact_id

    def test_create_event_failed_with_error(self) -> None:
        """Test creating failed event with error info."""
        event = WebhookEvent(
            event_type=WebhookEventType.CALL_FAILED,
            provider_call_id="CA123456",
            call_id="call-123",
            campaign_id=None,
            contact_id=None,
            status=CallStatus.FAILED,
            timestamp=datetime.now(timezone.utc),
            error_code="21211",
            error_message="Invalid phone number",
        )

        assert event.error_code == "21211"
        assert event.error_message == "Invalid phone number"


class TestCallStatus:
    """Tests for CallStatus enum."""

    def test_all_statuses_defined(self) -> None:
        """Test all expected statuses are defined."""
        expected = {
            "queued",
            "initiated",
            "ringing",
            "in_progress",
            "completed",
            "busy",
            "no_answer",
            "failed",
            "canceled",
        }

        actual = {s.value for s in CallStatus}
        assert actual == expected


class TestWebhookEventType:
    """Tests for WebhookEventType enum."""

    def test_all_event_types_defined(self) -> None:
        """Test all expected event types are defined."""
        expected = {
            "call.initiated",
            "call.ringing",
            "call.answered",
            "call.completed",
            "call.failed",
            "call.no_answer",
            "call.busy",
        }

        actual = {e.value for e in WebhookEventType}
        assert actual == expected


class TestTelephonyProviderError:
    """Tests for telephony provider exceptions."""

    def test_base_error(self) -> None:
        """Test base TelephonyProviderError."""
        error = TelephonyProviderError(
            message="Something went wrong",
            error_code="ERR001",
            provider_response={"error": "details"},
        )

        assert str(error) == "Something went wrong"
        assert error.error_code == "ERR001"
        assert error.provider_response == {"error": "details"}

    def test_call_initiation_error(self) -> None:
        """Test CallInitiationError."""
        error = CallInitiationError(
            message="Failed to initiate call",
            error_code="21211",
        )

        assert isinstance(error, TelephonyProviderError)
        assert str(error) == "Failed to initiate call"
        assert error.error_code == "21211"

    def test_webhook_parse_error(self) -> None:
        """Test WebhookParseError."""
        error = WebhookParseError(
            message="Invalid payload",
            error_code="PARSE_ERROR",
            provider_response={"invalid": "data"},
        )

        assert isinstance(error, TelephonyProviderError)
        assert str(error) == "Invalid payload"
        assert error.provider_response == {"invalid": "data"}