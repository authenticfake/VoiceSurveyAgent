from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.telephony.interface import (
    CallInitiationError,
    CallInitiationRequest,
    CallInitiationResponse,
    CallStatus,
    TelephonyProviderError,
    WebhookEvent,
    WebhookEventType,
    WebhookParseError,
)


class TestCallInitiationRequest:
    def test_create_request_minimal(self) -> None:
        req = CallInitiationRequest(
            to="+15550002222",
            from_number="+15550001111",
            callback_url="https://example.test/webhooks/telephony/events",
            call_id="call-001",
            campaign_id=uuid4(),
            contact_id=uuid4(),
        )
        assert req.to.startswith("+")
        assert req.language == "en"
        assert req.metadata == {}

    def test_create_request_full(self) -> None:
        req = CallInitiationRequest(
            to="+15550002222",
            from_number="+15550001111",
            callback_url="https://example.test/webhooks/telephony/events",
            call_id="call-001",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            language="it",
            metadata={"k": "v"},
        )
        assert req.language == "it"
        assert req.metadata["k"] == "v"


class TestCallInitiationResponse:
    def test_create_response(self) -> None:
        now = datetime.now(timezone.utc)
        resp = CallInitiationResponse(
            provider_call_id="CA123",
            status=CallStatus.QUEUED,
            created_at=now,
            raw_response={"sid": "CA123"},
        )
        assert resp.provider_call_id == "CA123"
        assert resp.status == CallStatus.QUEUED
        assert resp.created_at == now
        assert resp.raw_response["sid"] == "CA123"


class TestWebhookEvent:
    def test_create_event_minimal(self) -> None:
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
        now = datetime.now(timezone.utc)
        campaign_id = uuid4()
        contact_id = uuid4()

        event = WebhookEvent(
            event_type=WebhookEventType.CALL_COMPLETED,
            provider_call_id="CA123456",
            call_id="call-123",
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=CallStatus.COMPLETED,
            timestamp=now,
            duration_seconds=180,
        )

        assert event.duration_seconds == 180
        assert event.status == CallStatus.COMPLETED
