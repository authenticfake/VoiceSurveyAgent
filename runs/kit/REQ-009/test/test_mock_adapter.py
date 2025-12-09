"""
Tests for mock telephony adapter.

REQ-009: Telephony provider adapter interface
"""

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
    """Create fresh mock adapter for each test."""
    return MockTelephonyAdapter()


@pytest.fixture
def call_request() -> CallInitiationRequest:
    """Create test call request."""
    return CallInitiationRequest(
        to="+14155551234",
        from_number="+14155550000",
        callback_url="https://example.com/webhook",
        call_id="call-test-001",
        campaign_id=uuid4(),
        contact_id=uuid4(),
    )


class TestMockAdapterInitiateCall:
    """Tests for MockTelephonyAdapter.initiate_call method."""

    @pytest.mark.asyncio
    async def test_initiate_call_success(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        """Test successful call initiation."""
        response = await mock_adapter.initiate_call(call_request)

        assert response.provider_call_id.startswith("MOCK_CALL_")
        assert response.status == CallStatus.QUEUED
        assert response.raw_response["mock"] is True

    @pytest.mark.asyncio
    async def test_initiate_call_records_request(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        """Test that call request is recorded."""
        await mock_adapter.initiate_call(call_request)

        assert len(mock_adapter.calls) == 1
        assert mock_adapter.calls[0] == call_request
        assert mock_adapter.get_last_call() == call_request

    @pytest.mark.asyncio
    async def test_initiate_call_increments_call_id(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        """Test that provider call IDs are unique."""
        response1 = await mock_adapter.initiate_call(call_request)
        response2 = await mock_adapter.initiate_call(call_request)

        assert response1.provider_call_id != response2.provider_call_id
        assert "000001" in response1.provider_call_id
        assert "000002" in response2.provider_call_id

    @pytest.mark.asyncio
    async def test_initiate_call_configured_failure(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        """Test configured failure mode."""
        mock_adapter.configure_failure(
            should_fail=True,
            error_message="Test failure",
            error_code="TEST_ERROR",
        )

        with pytest.raises(CallInitiationError) as exc_info:
            await mock_adapter.initiate_call(call_request)

        assert str(exc_info.value) == "Test failure"
        assert exc_info.value.error_code == "TEST_ERROR"

    @pytest.mark.asyncio
    async def test_initiate_call_configured_status(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        """Test configured status."""
        mock_adapter.configure_status(CallStatus.RINGING)

        response = await mock_adapter.initiate_call(call_request)

        assert response.status == CallStatus.RINGING


class TestMockAdapterParseWebhook:
    """Tests for MockTelephonyAdapter.parse_webhook_event method."""

    def test_parse_valid_event(self, mock_adapter: MockTelephonyAdapter) -> None:
        """Test parsing valid webhook event."""
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

    def test_parse_event_records_webhook(
        self, mock_adapter: MockTelephonyAdapter
    ) -> None:
        """Test that webhook is recorded."""
        payload = {
            "event_type": "call.completed",
            "provider_call_id": "MOCK_CALL_001",
        }

        mock_adapter.parse_webhook_event(payload)

        assert len(mock_adapter.webhooks) == 1
        assert mock_adapter.webhooks[0] == payload

    def test_parse_missing_event_type_raises_error(
        self, mock_adapter: MockTelephonyAdapter
    ) -> None:
        """Test that missing event_type raises error."""
        payload = {
            "provider_call_id": "MOCK_CALL_001",
        }

        with pytest.raises(WebhookParseError) as exc_info:
            mock_adapter.parse_webhook_event(payload)

        assert exc_info.value.error_code == "MISSING_EVENT_TYPE"

    def test_parse_missing_provider_call_id_raises_error(
        self, mock_adapter: MockTelephonyAdapter
    ) -> None:
        """Test that missing provider_call_id raises error."""
        payload = {
            "event_type": "call.completed",
        }

        with pytest.raises(WebhookParseError) as exc_info:
            mock_adapter.parse_webhook_event(payload)

        assert exc_info.value.error_code == "MISSING_PROVIDER_CALL_ID"

    def test_parse_invalid_event_type_raises_error(
        self, mock_adapter: MockTelephonyAdapter
    ) -> None:
        """Test that invalid event_type raises error."""
        payload = {
            "event_type": "invalid.event",
            "provider_call_id": "MOCK_CALL_001",
        }

        with pytest.raises(WebhookParseError) as exc_info:
            mock_adapter.parse_webhook_event(payload)

        assert exc_info.value.error_code == "INVALID_EVENT_TYPE"


class TestMockAdapterSignatureValidation:
    """Tests for MockTelephonyAdapter.validate_webhook_signature method."""

    def test_validate_signature_always_true(
        self, mock_adapter: MockTelephonyAdapter
    ) -> None:
        """Test that mock always returns True for signature validation."""
        result = mock_adapter.validate_webhook_signature(
            payload=b"any_payload",
            signature="any_signature",
            url="https://example.com/webhook",
        )

        assert result is True


class TestMockAdapterReset:
    """Tests for MockTelephonyAdapter.reset method."""

    @pytest.mark.asyncio
    async def test_reset_clears_state(
        self,
        mock_adapter: MockTelephonyAdapter,
        call_request: CallInitiationRequest,
    ) -> None:
        """Test that reset clears all state."""
        # Add some state
        await mock_adapter.initiate_call(call_request)
        mock_adapter.parse_webhook_event({
            "event_type": "call.completed",
            "provider_call_id": "MOCK_CALL_001",
        })
        mock_adapter.configure_failure(should_fail=True)
        mock_adapter.configure_status(CallStatus.RINGING)

        # Reset
        mock_adapter.reset()

        # Verify state is cleared
        assert len(mock_adapter.calls) == 0
        assert len(mock_adapter.webhooks) == 0
        assert mock_adapter.get_last_call() is None

        # Verify failure mode is reset
        response = await mock_adapter.initiate_call(call_request)
        assert response.status == CallStatus.QUEUED  # Default status


class TestMockAdapterGenerateWebhookPayload:
    """Tests for MockTelephonyAdapter.generate_webhook_payload method."""

    def test_generate_minimal_payload(
        self, mock_adapter: MockTelephonyAdapter
    ) -> None:
        """Test generating minimal webhook payload."""
        payload = mock_adapter.generate_webhook_payload(
            event_type=WebhookEventType.CALL_COMPLETED,
            provider_call_id="MOCK_CALL_001",
        )

        assert payload["event_type"] == "call.completed"
        assert payload["provider_call_id"] == "MOCK_CALL_001"
        assert payload["status"] == "completed"

    def test_generate_full_payload(
        self, mock_adapter: MockTelephonyAdapter
    ) -> None:
        """Test generating full webhook payload."""
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = mock_adapter.generate_webhook_payload(
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

        assert payload["event_type"] == "call.failed"
        assert payload["provider_call_id"] == "MOCK_CALL_002"
        assert payload["call_id"] == "call-456"
        assert payload["campaign_id"] == str(campaign_id)
        assert payload["contact_id"] == str(contact_id)
        assert payload["status"] == "failed"
        assert payload["duration_seconds"] == 0
        assert payload["error_code"] == "21211"
        assert payload["error_message"] == "Invalid phone number"

    def test_generated_payload_can_be_parsed(
        self, mock_adapter: MockTelephonyAdapter
    ) -> None:
        """Test that generated payload can be parsed back."""
        campaign_id = uuid4()
        contact_id = uuid4()

        payload = mock_adapter.generate_webhook_payload(
            event_type=WebhookEventType.CALL_ANSWERED,
            provider_call_id="MOCK_CALL_003",
            call_id="call-789",
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=CallStatus.IN_PROGRESS,
        )

        event = mock_adapter.parse_webhook_event(payload)

        assert event.event_type == WebhookEventType.CALL_ANSWERED
        assert event.provider_call_id == "MOCK_CALL_003"
        assert event.call_id == "call-789"
        assert event.campaign_id == campaign_id
        assert event.contact_id == contact_id