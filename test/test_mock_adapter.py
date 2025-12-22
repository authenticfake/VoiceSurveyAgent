"""Tests for mock telephony adapter (sync-only)."""

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
def mock_adapter() -> MockTelephonyAdapter:
    return MockTelephonyAdapter()


@pytest.fixture
def call_request() -> CallInitiationRequest:
    return CallInitiationRequest(
        to="+14155551234",
        from_number="+14155550000",
        callback_url="https://example.com/webhook",
        call_id="call-test-001",
        campaign_id=uuid4(),
        contact_id=uuid4(),
    )


class TestMockAdapterInitiateCallSync:
    def test_initiate_call_success(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        response = mock_adapter.initiate_call_sync(call_request)

        assert response.provider_call_id.startswith("MOCK_CALL_")
        assert response.status == CallStatus.QUEUED
        assert response.raw_response["mock"] is True

    def test_initiate_call_records_request(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        mock_adapter.initiate_call_sync(call_request)

        assert len(mock_adapter.calls) == 1
        assert mock_adapter.calls[0] == call_request
        assert mock_adapter.get_last_call() == call_request

    def test_initiate_call_increments_call_id(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        response1 = mock_adapter.initiate_call_sync(call_request)
        response2 = mock_adapter.initiate_call_sync(call_request)

        assert response1.provider_call_id != response2.provider_call_id
        assert "000001" in response1.provider_call_id
        assert "000002" in response2.provider_call_id

    def test_initiate_call_configured_failure(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        mock_adapter.configure_failure(
            should_fail=True,
            error_message="Test failure",
            error_code="TEST_ERROR",
        )

        with pytest.raises(CallInitiationError) as exc_info:
            mock_adapter.initiate_call_sync(call_request)

        assert str(exc_info.value) == "Test failure"
        assert exc_info.value.error_code == "TEST_ERROR"

    def test_initiate_call_configured_status(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        mock_adapter.configure_status(CallStatus.RINGING)

        response = mock_adapter.initiate_call_sync(call_request)
        assert response.status == CallStatus.RINGING


class TestMockAdapterParseWebhook:
    def test_parse_valid_event(self, mock_adapter: MockTelephonyAdapter) -> None:
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = {
            "event_type": "call.answered",
            "provider_call_id": "MOCK_CALL_001",
            "call_id": "call-123",
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
            "status": "in_progress",
        }

        event = mock_adapter.parse_webhook_event(payload)

        assert event.event_type == WebhookEventType.CALL_ANSWERED
        assert event.provider_call_id == "MOCK_CALL_001"
        assert event.call_id == "call-123"
        assert event.campaign_id == campaign_id
        assert event.contact_id == contact_id
        assert event.status == CallStatus.IN_PROGRESS

    def test_parse_event_records_webhook(self, mock_adapter: MockTelephonyAdapter) -> None:
        payload = {"event_type": "call.completed", "provider_call_id": "MOCK_CALL_001"}

        mock_adapter.parse_webhook_event(payload)

        assert len(mock_adapter.webhooks) == 1
        assert mock_adapter.webhooks[0] == payload

    def test_parse_missing_event_type_raises_error(
        self, mock_adapter: MockTelephonyAdapter
    ) -> None:
        payload = {"provider_call_id": "MOCK_CALL_001"}

        with pytest.raises(WebhookParseError) as exc_info:
            mock_adapter.parse_webhook_event(payload)

        assert exc_info.value.error_code == "MISSING_EVENT_TYPE"


class TestMockAdapterReset:
    def test_reset_clears_state(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        mock_adapter.initiate_call_sync(call_request)
        mock_adapter.parse_webhook_event(
            {"event_type": "call.completed", "provider_call_id": "MOCK_CALL_001"}
        )

        assert len(mock_adapter.calls) == 1
        assert len(mock_adapter.webhooks) == 1

        mock_adapter.reset()

        assert len(mock_adapter.calls) == 0
        assert len(mock_adapter.webhooks) == 0
