"""
Twilio telephony provider adapter.

REQ-009: Telephony provider adapter interface
- Concrete adapter implements Twilio-compatible API
- Adapter configurable via ProviderConfig entity
"""

import hashlib
import hmac
import logging
from base64 import b64encode
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import anyio
import httpx

from app.telephony.config import TelephonyConfig, get_telephony_config
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

TWILIO_STATUS_MAP: dict[str, CallStatus] = {
    "queued": CallStatus.QUEUED,
    "initiated": CallStatus.INITIATED,
    "ringing": CallStatus.RINGING,
    "in-progress": CallStatus.IN_PROGRESS,
    "completed": CallStatus.COMPLETED,
    "busy": CallStatus.BUSY,
    "no-answer": CallStatus.NO_ANSWER,
    "failed": CallStatus.FAILED,
    "canceled": CallStatus.CANCELED,
}

TWILIO_EVENT_MAP: dict[str, WebhookEventType] = {
    "initiated": WebhookEventType.CALL_INITIATED,
    "ringing": WebhookEventType.CALL_RINGING,
    "in-progress": WebhookEventType.CALL_ANSWERED,
    "completed": WebhookEventType.CALL_COMPLETED,
    "failed": WebhookEventType.CALL_FAILED,
    "no-answer": WebhookEventType.CALL_NO_ANSWER,
    "busy": WebhookEventType.CALL_BUSY,
}


class TwilioAdapter(TelephonyProvider):
    """Twilio telephony provider adapter.

    Uses httpx for HTTP requests. The async entrypoint remains available
    for backward compatibility and delegates to the sync implementation.
    """

    def __init__(
        self,
        config: TelephonyConfig | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._config = config or get_telephony_config()
        self._http_client = http_client
        self._owns_client = http_client is None

    def _get_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=httpx.Timeout(30.0))
        return self._http_client

    def close(self) -> None:
        if self._owns_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def _get_auth(self) -> tuple[str, str]:
        return (self._config.twilio_account_sid, self._config.twilio_auth_token)

    def _get_api_url(self, endpoint: str) -> str:
        account_sid = self._config.twilio_account_sid
        return f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}{endpoint}"

    async def initiate_call(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Async wrapper for backward compatibility."""
        return await anyio.to_thread.run_sync(self.initiate_call_sync, request)

    def initiate_call_sync(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Initiate an outbound call via Twilio (sync)."""
        client = self._get_client()

        payload = {
            "To": request.to,
            "From": request.from_number,
            "StatusCallback": request.callback_url,
            "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"],
            "StatusCallbackMethod": "POST",
            "Url": f"{self._config.webhook_base_url}/webhooks/telephony/twiml",
            "Method": "POST",
        }

        metadata = {
            "call_id": request.call_id,
            "campaign_id": str(request.campaign_id),
            "contact_id": str(request.contact_id),
            "language": request.language,
            **request.metadata,
        }

        callback_with_meta = f"{request.callback_url}?{urlencode(metadata)}"
        payload["StatusCallback"] = callback_with_meta

        logger.info(
            "Initiating Twilio call",
            extra={
                "to": request.to,
                "call_id": request.call_id,
                "campaign_id": str(request.campaign_id),
            },
        )

        try:
            response = client.post(
                self._get_api_url("/Calls.json"),
                data=payload,
                auth=self._get_auth(),
            )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                logger.error(
                    "Twilio call initiation failed",
                    extra={
                        "status_code": response.status_code,
                        "error": error_data,
                        "call_id": request.call_id,
                    },
                )
                raise CallInitiationError(
                    message=error_data.get("message", "Call initiation failed"),
                    error_code=str(error_data.get("code", response.status_code)),
                    provider_response=error_data,
                )

            data = response.json()

            return CallInitiationResponse(
                provider_call_id=data["sid"],
                status=TWILIO_STATUS_MAP.get(data["status"], CallStatus.QUEUED),
                created_at=datetime.fromisoformat(
                    data["date_created"].replace("Z", "+00:00")
                )
                if data.get("date_created")
                else datetime.now(timezone.utc),
                raw_response=data,
            )

        except httpx.HTTPError as e:
            logger.exception(
                "HTTP error during Twilio call initiation",
                extra={"call_id": request.call_id},
            )
            raise CallInitiationError(
                message=f"HTTP error: {e!s}",
                error_code="HTTP_ERROR",
            ) from e

    def parse_webhook_event(self, payload: dict[str, Any]) -> WebhookEvent:
        try:
            call_sid = payload.get("CallSid")
            call_status = payload.get("CallStatus", "").lower()

            if not call_sid:
                raise WebhookParseError(
                    message="Missing CallSid in webhook payload",
                    error_code="MISSING_CALL_SID",
                    provider_response=payload,
                )

            if not call_status:
                raise WebhookParseError(
                    message="Missing CallStatus in webhook payload",
                    error_code="MISSING_CALL_STATUS",
                    provider_response=payload,
                )

            event_type = TWILIO_EVENT_MAP.get(call_status) or WebhookEventType.CALL_COMPLETED
            status = TWILIO_STATUS_MAP.get(call_status, CallStatus.COMPLETED)

            call_id = payload.get("call_id")
            campaign_id_str = payload.get("campaign_id")
            contact_id_str = payload.get("contact_id")

            from uuid import UUID

            campaign_id = UUID(campaign_id_str) if campaign_id_str else None
            contact_id = UUID(contact_id_str) if contact_id_str else None

            duration_seconds = None
            if call_status == "completed" and payload.get("CallDuration"):
                try:
                    duration_seconds = int(payload["CallDuration"])
                except (ValueError, TypeError):
                    pass

            error_code = None
            error_message = None
            if call_status == "failed":
                error_code = payload.get("ErrorCode")
                error_message = payload.get("ErrorMessage")

            timestamp = datetime.now(timezone.utc)
            if payload.get("Timestamp"):
                try:
                    timestamp = datetime.fromisoformat(
                        payload["Timestamp"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            return WebhookEvent(
                event_type=event_type,
                provider_call_id=call_sid,
                call_id=call_id,
                campaign_id=campaign_id,
                contact_id=contact_id,
                status=status,
                timestamp=timestamp,
                duration_seconds=duration_seconds,
                error_code=error_code,
                error_message=error_message,
                raw_payload=payload,
            )

        except WebhookParseError:
            raise
        except Exception as e:
            logger.exception("Error parsing Twilio webhook")
            raise WebhookParseError(
                message=f"Failed to parse webhook: {e!s}",
                error_code="PARSE_ERROR",
                provider_response=payload,
            ) from e

    def validate_webhook_signature(self, payload: bytes, signature: str, url: str) -> bool:
        if not self._config.twilio_auth_token:
            logger.warning("No auth token configured, skipping signature validation")
            return True

        try:
            from urllib.parse import parse_qs

            params = parse_qs(payload.decode("utf-8"))

            data_str = url
            for key in sorted(params.keys()):
                data_str += key + params[key][0]

            computed = hmac.new(
                self._config.twilio_auth_token.encode("utf-8"),
                data_str.encode("utf-8"),
                hashlib.sha1,
            ).digest()

            computed_sig = b64encode(computed).decode("utf-8")
            return hmac.compare_digest(computed_sig, signature)

        except Exception:
            logger.exception("Error validating Twilio signature")
            return False
