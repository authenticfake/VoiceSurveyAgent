"""
Mock telephony provider adapter for testing.

REQ-009 constraints:
- synchronous
- fast
- no DB/ORM
"""

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


def _normalize_status(value: str) -> str:
    """Accept both Twilio-style and snake_case style statuses."""
    v = value.strip().lower()
    return v.replace("_", "-")


class MockTelephonyAdapter(TelephonyProvider):
    def __init__(self) -> None:
        self._calls: list[CallInitiationRequest] = []
        self._webhooks: list[dict[str, Any]] = []
        self._next_call_id: int = 1
        self._should_fail: bool = False
        self._fail_error: str = "Mock failure"
        self._fail_code: str = "MOCK_ERROR"
        self._default_status: CallStatus = CallStatus.QUEUED

    # -------- Compatibility helpers (useful + zero cost) --------

    @property
    def calls(self) -> list[CallInitiationRequest]:
        return list(self._calls)

    @property
    def webhooks(self) -> list[dict[str, Any]]:
        return list(self._webhooks)

    def configure_status(self, status: CallStatus) -> None:
        self._default_status = status

    def validate_webhook_signature(self, payload: bytes, signature: str, url: str) -> bool:  # noqa: ARG002
        # Mock always accepts
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
        payload: dict[str, Any] = {
            "event_type": event_type.value,
            "provider_call_id": provider_call_id,
        }
        if call_id is not None:
            payload["call_id"] = call_id
        if campaign_id is not None:
            payload["campaign_id"] = str(campaign_id)
        if contact_id is not None:
            payload["contact_id"] = str(contact_id)
        if status is not None:
            payload["status"] = status.value
        if duration_seconds is not None:
            payload["duration_seconds"] = duration_seconds
        if error_code is not None:
            payload["error_code"] = error_code
        if error_message is not None:
            payload["error_message"] = error_message
        return payload

    # -------- Core behaviour --------

    def reset(self) -> None:
        self._calls.clear()
        self._webhooks.clear()
        self._next_call_id = 1
        self._should_fail = False
        self._default_status = CallStatus.QUEUED

    def configure_failure(
        self,
        should_fail: bool = True,
        error_message: str = "Mock failure",
        error_code: str = "MOCK_ERROR",
    ) -> None:
        self._should_fail = should_fail
        self._fail_error = error_message
        self._fail_code = error_code

    def initiate_call(self, request: CallInitiationRequest) -> CallInitiationResponse:
        self._calls.append(request)

        if self._should_fail:
            self._should_fail = False
            raise CallInitiationError(
                message=self._fail_error,
                error_code=self._fail_code,
                provider_response={},
            )

        provider_call_id = f"MOCK_CALL_{self._next_call_id:03d}"
        self._next_call_id += 1

        return CallInitiationResponse(
            provider_call_id=provider_call_id,
            status=self._default_status,
            created_at=datetime.now(timezone.utc),
            raw_response={"mock": True},
        )

    def parse_webhook_event(self, payload: dict[str, Any]) -> WebhookEvent:
        self._webhooks.append(payload)

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

        try:
            event_type = WebhookEventType(payload["event_type"])
        except ValueError as exc:
            raise WebhookParseError(
                message=str(exc),
                error_code="INVALID_EVENT_TYPE",
                provider_response=payload,
            )

        raw_status = payload.get("status", CallStatus.COMPLETED.value)
        normalized = _normalize_status(str(raw_status))
        status = CallStatus(normalized) if normalized in {s.value for s in CallStatus} else CallStatus.COMPLETED

        campaign_id = None
        contact_id = None
        if payload.get("campaign_id"):
            try:
                campaign_id = UUID(str(payload["campaign_id"]))
            except (ValueError, TypeError):
                campaign_id = None
        if payload.get("contact_id"):
            try:
                contact_id = UUID(str(payload["contact_id"]))
            except (ValueError, TypeError):
                contact_id = None

        return WebhookEvent(
            event_type=event_type,
            provider_call_id=str(payload["provider_call_id"]),
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
