"""
Mock telephony provider adapter for testing.

REQ-009: Telephony provider adapter interface
- Adapter is injectable for testing with mock provider
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.telephony.interface import (
    CallInitiationError,
    CallInitiationRequest,
    CallInitiationResponse,
    CallStatus,
    TelephonyProvider,
    WebhookEvent,
    WebhookEventType,
    WebhookParseError,
)

logger = logging.getLogger(__name__)


class MockTelephonyAdapter(TelephonyProvider):
    """Mock telephony provider for testing.

    Records all calls and allows configuring responses for testing
    different scenarios.
    """

    def __init__(self) -> None:
        """Initialize mock adapter."""
        self._calls: list[CallInitiationRequest] = []
        self._webhooks: list[dict[str, Any]] = []
        self._next_call_id: int = 1
        self._should_fail: bool = False
        self._fail_error: str = "Mock failure"
        self._fail_code: str = "MOCK_ERROR"
        self._default_status: CallStatus = CallStatus.QUEUED

    def reset(self) -> None:
        """Reset mock state."""
        self._calls.clear()
        self._webhooks.clear()
        self._next_call_id = 1
        self._should_fail = False
        self._fail_error = "Mock failure"
        self._fail_code = "MOCK_ERROR"
        self._default_status = CallStatus.QUEUED

    def configure_failure(
        self,
        should_fail: bool = True,
        error_message: str = "Mock failure",
        error_code: str = "MOCK_ERROR",
    ) -> None:
        """Configure mock to fail on next call.

        Args:
            should_fail: Whether to fail.
            error_message: Error message to return.
            error_code: Error code to return.
        """
        self._should_fail = should_fail
        self._fail_error = error_message
        self._fail_code = error_code

    def configure_status(self, status: CallStatus) -> None:
        """Configure default status for initiated calls.

        Args:
            status: Status to return for new calls.
        """
        self._default_status = status

    @property
    def calls(self) -> list[CallInitiationRequest]:
        """Get list of initiated calls."""
        return self._calls.copy()

    @property
    def webhooks(self) -> list[dict[str, Any]]:
        """Get list of parsed webhooks."""
        return self._webhooks.copy()

    def get_last_call(self) -> CallInitiationRequest | None:
        """Get the last initiated call.

        Returns:
            Last call request or None.
        """
        return self._calls[-1] if self._calls else None

    async def initiate_call(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Mock call initiation.

        Args:
            request: Call initiation request.

        Returns:
            Mock response.

        Raises:
            CallInitiationError: If configured to fail.
        """
        logger.info(
            "Mock: Initiating call",
            extra={
                "to": request.to,
                "call_id": request.call_id,
            },
        )

        if self._should_fail:
            raise CallInitiationError(
                message=self._fail_error,
                error_code=self._fail_code,
            )

        self._calls.append(request)

        provider_call_id = f"MOCK_CALL_{self._next_call_id:06d}"
        self._next_call_id += 1

        return CallInitiationResponse(
            provider_call_id=provider_call_id,
            status=self._default_status,
            created_at=datetime.now(timezone.utc),
            raw_response={
                "mock": True,
                "call_id": request.call_id,
                "provider_call_id": provider_call_id,
            },
        )

    def parse_webhook_event(
        self,
        payload: dict[str, Any],
    ) -> WebhookEvent:
        """Parse mock webhook event.

        Args:
            payload: Webhook payload.

        Returns:
            Parsed event.

        Raises:
            WebhookParseError: If payload is invalid.
        """
        self._webhooks.append(payload)

        # Validate required fields
        if "event_type" not in payload:
            raise WebhookParseError(
                message="Missing event_type in payload",
                error_code="MISSING_EVENT_TYPE",
                provider_response=payload,
            )

        if "provider_call_id" not in payload:
            raise WebhookParseError(
                message="Missing provider_call_id in payload",
                error_code="MISSING_PROVIDER_CALL_ID",
                provider_response=payload,
            )

        # Parse event type
        try:
            event_type = WebhookEventType(payload["event_type"])
        except ValueError:
            raise WebhookParseError(
                message=f"Invalid event_type: {payload['event_type']}",
                error_code="INVALID_EVENT_TYPE",
                provider_response=payload,
            )

        # Parse status
        status_str = payload.get("status", "completed")
        try:
            status = CallStatus(status_str)
        except ValueError:
            status = CallStatus.COMPLETED

        # Parse UUIDs
        campaign_id = None
        contact_id = None
        if payload.get("campaign_id"):
            try:
                campaign_id = UUID(payload["campaign_id"])
            except (ValueError, TypeError):
                pass
        if payload.get("contact_id"):
            try:
                contact_id = UUID(payload["contact_id"])
            except (ValueError, TypeError):
                pass

        return WebhookEvent(
            event_type=event_type,
            provider_call_id=payload["provider_call_id"],
            call_id=payload.get("call_id"),
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=status,
            timestamp=datetime.now(timezone.utc),
            duration_seconds=payload.get("duration_seconds"),
            error_code=payload.get("error_code"),
            error_message=payload.get("error_message"),
            raw_payload=payload,
        )

    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        url: str,
    ) -> bool:
        """Mock signature validation.

        Always returns True for testing.

        Args:
            payload: Request body.
            signature: Signature header.
            url: Webhook URL.

        Returns:
            Always True.
        """
        return True

    def generate_webhook_payload(
        self,
        event_type: WebhookEventType,
        provider_call_id: str,
        call_id: str | None = None,
        campaign_id: UUID | None = None,
        contact_id: UUID | None = None,
        status: CallStatus | None = None,
        duration_seconds: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        """Generate a mock webhook payload for testing.

        Args:
            event_type: Type of event.
            provider_call_id: Provider call ID.
            call_id: Internal call ID.
            campaign_id: Campaign UUID.
            contact_id: Contact UUID.
            status: Call status.
            duration_seconds: Call duration.
            error_code: Error code.
            error_message: Error message.

        Returns:
            Mock webhook payload.
        """
        payload: dict[str, Any] = {
            "event_type": event_type.value,
            "provider_call_id": provider_call_id,
            "status": (status or CallStatus.COMPLETED).value,
        }

        if call_id:
            payload["call_id"] = call_id
        if campaign_id:
            payload["campaign_id"] = str(campaign_id)
        if contact_id:
            payload["contact_id"] = str(contact_id)
        if duration_seconds is not None:
            payload["duration_seconds"] = duration_seconds
        if error_code:
            payload["error_code"] = error_code
        if error_message:
            payload["error_message"] = error_message

        return payload