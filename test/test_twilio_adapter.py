"""
Tests for TwilioAdapter (synchronous).

REQ-009 constraints:
- synchronous
- fast
- no DB / ORM
- no real HTTP calls
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
    WebhookParseError,
)
from app.telephony.twilio_adapter import TwilioAdapter


@pytest.fixture
def config() -> TelephonyConfig:
    return TelephonyConfig(
        provider_type=ProviderType.TWILIO,
        twilio_account_sid="AC123",
        twilio_auth_token="secret",
        twilio_from_number="+15550001111",
        webhook_base_url="https://example.test",
    )


@pytest.fixture
def call_request() -> CallInitiationRequest:
    return CallInitiationRequest(
        to="+15550002222",
        from_number="+15550001111",
        callback_url="https://example.test/webhooks/telephony/events",
        call_id="call-001",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        language="it",
        metadata={"k": "v"},
    )


def test_initiate_call_success_maps_response_fields(config: TelephonyConfig, call_request: CallInitiationRequest) -> None:
    http_client = MagicMock(spec=httpx.Client)
    http_client.post.return_value = httpx.Response(
        status_code=201,
        json={"sid": "CA123", "status": "queued"},
    )

    adapter = TwilioAdapter(config=config, http_client=http_client)

    resp = adapter.initiate_call(call_request)

    assert resp.provider_call_id == "CA123"
    assert isinstance(resp.status, CallStatus)

    http_client.post.assert_called_once()
    called_url = http_client.post.call_args.args[0]
    assert "/Accounts/AC123/Calls.json" in called_url


def test_initiate_call_raises_on_http_error(config: TelephonyConfig, call_request: CallInitiationRequest) -> None:
    http_client = MagicMock(spec=httpx.Client)
    http_client.post.return_value = httpx.Response(
        status_code=400,
        json={"code": 123, "message": "bad request"},
    )

    adapter = TwilioAdapter(config=config, http_client=http_client)

    with pytest.raises(CallInitiationError):
        adapter.initiate_call(call_request)


def test_parse_webhook_event_rejects_missing_required_fields(config: TelephonyConfig) -> None:
    adapter = TwilioAdapter(config=config, http_client=MagicMock(spec=httpx.Client))

    with pytest.raises(WebhookParseError):
        adapter.parse_webhook_event(payload={"CallStatus": "completed"})
