"""Tests for Twilio telephony adapter (sync-only).

REQ-009 constraints for logic tests:
- sync
- fast
- no DB
- no SQLAlchemy
"""

from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest

from app.telephony.config import ProviderType, TelephonyConfig
from app.telephony.interface import (
    CallInitiationError,
    CallInitiationRequest,
    CallStatus,
    WebhookEventType,
    WebhookParseError,
)
from app.telephony.twilio_adapter import TwilioAdapter


@pytest.fixture
def twilio_config() -> TelephonyConfig:
    return TelephonyConfig(
        provider_type=ProviderType.TWILIO,
        twilio_account_sid="AC_TEST_ACCOUNT_SID",
        twilio_auth_token="test_auth_token_12345",
        twilio_from_number="+14155550000",
        webhook_base_url="https://example.com",
        max_concurrent_calls=10,
        call_timeout_seconds=60,
    )


@pytest.fixture
def call_request() -> CallInitiationRequest:
    return CallInitiationRequest(
        to="+14155551234",
        from_number="+14155550000",
        callback_url="https://example.com/webhooks/telephony/events",
        call_id="call-test-123",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        language="en",
    )


class TestTwilioAdapterInitiateCallSync:
    def test_initiate_call_success(
        self,
        twilio_config: TelephonyConfig,
        call_request: CallInitiationRequest,
    ) -> None:
        mock_response = httpx.Response(
            status_code=201,
            json={
                "sid": "CA_TEST_CALL_SID_123",
                "status": "queued",
                "date_created": "2024-01-15T10:30:00Z",
                "to": call_request.to,
                "from": call_request.from_number,
            },
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        adapter = TwilioAdapter(config=twilio_config, http_client=mock_client)
        response = adapter.initiate_call_sync(call_request)

        assert response.provider_call_id == "CA_TEST_CALL_SID_123"
        assert response.status == CallStatus.QUEUED
        assert response.raw_response["sid"] == "CA_TEST_CALL_SID_123"

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "Calls.json" in call_args[0][0]

    def test_initiate_call_api_error(
        self,
        twilio_config: TelephonyConfig,
        call_request: CallInitiationRequest,
    ) -> None:
        mock_response = httpx.Response(
            status_code=400,
            json={"code": 21211, "message": "Invalid 'To' Phone Number"},
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        adapter = TwilioAdapter(config=twilio_config, http_client=mock_client)

        with pytest.raises(CallInitiationError) as exc_info:
            adapter.initiate_call_sync(call_request)

        assert "Invalid 'To' Phone Number" in str(exc_info.value)
        assert exc_info.value.error_code == "21211"

    def test_initiate_call_http_error(
        self,
        twilio_config: TelephonyConfig,
        call_request: CallInitiationRequest,
    ) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        adapter = TwilioAdapter(config=twilio_config, http_client=mock_client)

        with pytest.raises(CallInitiationError) as exc_info:
            adapter.initiate_call_sync(call_request)

        assert exc_info.value.error_code == "HTTP_ERROR"

    def test_initiate_call_includes_metadata_in_callback(
        self,
        twilio_config: TelephonyConfig,
    ) -> None:
        campaign_id = uuid4()
        contact_id = uuid4()

        request = CallInitiationRequest(
            to="+14155551234",
            from_number="+14155550000",
            callback_url="https://example.com/webhooks/telephony/events",
            call_id="call-meta-test",
            campaign_id=campaign_id,
            contact_id=contact_id,
            language="it",
            metadata={"custom": "value"},
        )

        mock_response = httpx.Response(
            status_code=201,
            json={
                "sid": "CA_TEST",
                "status": "queued",
                "date_created": "2024-01-15T10:30:00Z",
            },
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        adapter = TwilioAdapter(config=twilio_config, http_client=mock_client)
        adapter.initiate_call_sync(request)

        call_args = mock_client.post.call_args
        data = call_args[1]["data"]
        callback_url = data["StatusCallback"]

        assert "call_id=call-meta-test" in callback_url
        assert f"campaign_id={campaign_id}" in callback_url
        assert f"contact_id={contact_id}" in callback_url
        assert "language=it" in callback_url


class TestTwilioAdapterParseWebhook:
    @pytest.fixture
    def adapter(self, twilio_config: TelephonyConfig) -> TwilioAdapter:
        return TwilioAdapter(config=twilio_config)

    def test_parse_answered_event(self, adapter: TwilioAdapter) -> None:
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = {
            "CallSid": "CA_TEST_123",
            "CallStatus": "in-progress",
            "call_id": "call-123",
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
        }

        event = adapter.parse_webhook_event(payload)

        assert event.event_type == WebhookEventType.CALL_ANSWERED
        assert event.provider_call_id == "CA_TEST_123"
        assert event.call_id == "call-123"
        assert event.campaign_id == campaign_id
        assert event.contact_id == contact_id
        assert event.status == CallStatus.IN_PROGRESS

    def test_parse_completed_event_with_duration(self, adapter: TwilioAdapter) -> None:
        payload = {
            "CallSid": "CA_TEST_456",
            "CallStatus": "completed",
            "CallDuration": "180",
            "call_id": "call-456",
        }

        event = adapter.parse_webhook_event(payload)

        assert event.event_type == WebhookEventType.CALL_COMPLETED
        assert event.status == CallStatus.COMPLETED
        assert event.duration_seconds == 180

    def test_parse_missing_call_sid_raises_error(self, adapter: TwilioAdapter) -> None:
        payload = {"CallStatus": "completed"}

        with pytest.raises(WebhookParseError) as exc_info:
            adapter.parse_webhook_event(payload)

        assert exc_info.value.error_code == "MISSING_CALL_SID"


class TestTwilioAdapterSignatureValidation:
    def test_validate_signature_no_auth_token(self) -> None:
        config = TelephonyConfig(
            provider_type=ProviderType.TWILIO,
            twilio_account_sid="AC_TEST",
            twilio_auth_token="",
            twilio_from_number="+14155550000",
        )

        adapter = TwilioAdapter(config=config)

        result = adapter.validate_webhook_signature(
            payload=b"test",
            signature="any_signature",
            url="https://example.com/webhook",
        )

        assert result is True
