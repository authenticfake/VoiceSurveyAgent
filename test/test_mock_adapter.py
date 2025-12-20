from __future__ import annotations

from uuid import uuid4

import pytest

from app.telephony.interface import (
    CallInitiationError,
    CallInitiationRequest,
    CallStatus,
    WebhookEventType,
    WebhookParseError,
)
from app.telephony.mock_adapter import MockTelephonyAdapter


@pytest.fixture
def adapter() -> MockTelephonyAdapter:
    return MockTelephonyAdapter()


@pytest.fixture
def call_request() -> CallInitiationRequest:
    return CallInitiationRequest(
        to="+14155551234",
        from_number="+14155550000",
        callback_url="https://example.com/webhook",
        call_id="call-123",
        campaign_id=uuid4(),
        contact_id=uuid4(),
    )


def test_initiate_call_success(adapter: MockTelephonyAdapter, call_request: CallInitiationRequest) -> None:
    response = adapter.initiate_call(call_request)
    assert response.provider_call_id.startswith("MOCK_CALL_")
    assert response.status == CallStatus.QUEUED


def test_initiate_call_records_request(adapter: MockTelephonyAdapter, call_request: CallInitiationRequest) -> None:
    adapter.initiate_call(call_request)
    assert len(adapter.calls) == 1
    assert adapter.calls[0].call_id == "call-123"


def test_initiate_call_increments_call_id(adapter: MockTelephonyAdapter, call_request: CallInitiationRequest) -> None:
    r1 = adapter.initiate_call(call_request)
    r2 = adapter.initiate_call(call_request)
    assert r1.provider_call_id != r2.provider_call_id


def test_initiate_call_configured_failure(adapter: MockTelephonyAdapter, call_request: CallInitiationRequest) -> None:
    adapter.configure_failure(should_fail=True, error_message="Test failure", error_code="TEST_ERROR")
    with pytest.raises(CallInitiationError) as exc:
        adapter.initiate_call(call_request)
    assert str(exc.value) == "Test failure"
    assert exc.value.error_code == "TEST_ERROR"


def test_configure_status(adapter: MockTelephonyAdapter, call_request: CallInitiationRequest) -> None:
    adapter.configure_status(CallStatus.RINGING)
    r = adapter.initiate_call(call_request)
    assert r.status == CallStatus.RINGING


def test_parse_valid_event_accepts_snake_case_status(adapter: MockTelephonyAdapter) -> None:
    campaign_id = uuid4()
    contact_id = uuid4()

    payload = {
        "event_type": WebhookEventType.CALL_ANSWERED.value,
        "provider_call_id": "MOCK_CALL_001",
        "call_id": "call-123",
        "campaign_id": str(campaign_id),
        "contact_id": str(contact_id),
        "status": "in_progress",  # legacy style
    }

    event = adapter.parse_webhook_event(payload)
    assert event.event_type == WebhookEventType.CALL_ANSWERED
    assert event.provider_call_id == "MOCK_CALL_001"
    assert event.call_id == "call-123"
    assert event.campaign_id == campaign_id
    assert event.contact_id == contact_id
    assert event.status == CallStatus.IN_PROGRESS


def test_parse_event_records_webhook(adapter: MockTelephonyAdapter) -> None:
    payload = {"event_type": WebhookEventType.CALL_COMPLETED.value, "provider_call_id": "MOCK_CALL_001"}
    adapter.parse_webhook_event(payload)
    assert len(adapter.webhooks) == 1


def test_validate_signature_always_true(adapter: MockTelephonyAdapter) -> None:
    assert adapter.validate_webhook_signature(payload=b"x", signature="sig", url="https://example.com") is True


def test_generate_webhook_payload_roundtrip(adapter: MockTelephonyAdapter) -> None:
    campaign_id = uuid4()
    contact_id = uuid4()

    payload = adapter.generate_webhook_payload(
        event_type=WebhookEventType.CALL_FAILED,
        provider_call_id="MOCK_CALL_002",
        call_id="call-456",
        campaign_id=campaign_id,
        contact_id=contact_id,
        status=CallStatus.FAILED,
        duration_seconds=0,
        error_code="21211",
        error_message="Invalid phone number",
    )

    event = adapter.parse_webhook_event(payload)
    assert event.event_type == WebhookEventType.CALL_FAILED
    assert event.provider_call_id == "MOCK_CALL_002"
    assert event.duration_seconds == 0
    assert event.error_code == "21211"
    assert event.error_message == "Invalid phone number"


def test_parse_rejects_invalid_payload(adapter: MockTelephonyAdapter) -> None:
    with pytest.raises(WebhookParseError):
        adapter.parse_webhook_event({})
