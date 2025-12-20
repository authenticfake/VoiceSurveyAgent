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


class TwilioAdapter(TelephonyProvider):
    """Twilio telephony provider adapter.

    Implements the TelephonyProvider interface for Twilio's REST API.
    Uses httpx for synchronous HTTP requests.
    """

    def __init__(
        self,
        config: TelephonyConfig | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Initialize Twilio adapter.

        Args:
            config: Telephony configuration. Uses default if not provided.
            http_client: HTTP client for API calls. Creates new if not provided.
        """
        self._config = config or get_telephony_config()
        self._http_client = http_client
        self._owns_client = http_client is None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=httpx.Timeout(30.0),
            )
        return self._http_client

    def close(self) -> None:
        """Close HTTP client if owned by this adapter."""
        if self._owns_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def _get_auth(self) -> tuple[str, str]:
        """Get HTTP basic auth credentials."""
        return (self._config.twilio_account_sid, self._config.twilio_auth_token)

    def _get_api_url(self, path: str) -> str:
        """Build Twilio API URL for account."""
        return (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self._config.twilio_account_sid}{path}"
        )

    def _map_status(self, status: str | None) -> CallStatus:
        """Map Twilio status string to CallStatus enum."""
        if not status:
            return CallStatus.UNKNOWN

        status_lower = status.lower()
        mapping: dict[str, CallStatus] = {
            "queued": CallStatus.QUEUED,
            "initiated": CallStatus.INITIATED,
            "ringing": CallStatus.RINGING,
            "in-progress": CallStatus.IN_PROGRESS,
            "completed": CallStatus.COMPLETED,
            "failed": CallStatus.FAILED,
            "busy": CallStatus.BUSY,
            "no-answer": CallStatus.NO_ANSWER,
            "canceled": CallStatus.CANCELED,
        }
        return mapping.get(status_lower, CallStatus.UNKNOWN)

    def initiate_call(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Initiate an outbound call via Twilio."""
        client = self._get_client()

        payload = {
            "To": request.to,
            "From": request.from_number,
            "StatusCallback": request.callback_url,
            "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"],
            "StatusCallbackMethod": "POST",
            "Url": f"{request.callback_url}?{urlencode({'call_id': request.call_id, 'campaign_id': str(request.campaign_id), 'contact_id': str(request.contact_id)})}",
        }

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

            logger.info(
                "Twilio call initiated successfully",
                extra={
                    "provider_call_id": data.get("sid"),
                    "call_id": request.call_id,
                    "status": data.get("status"),
                },
            )

            return CallInitiationResponse(
                provider_call_id=str(data.get("sid", "")),
                status=self._map_status(data.get("status")),
                created_at=datetime.now(timezone.utc),
                raw_response=data,
            )

        except httpx.HTTPError as exc:
            logger.exception("Twilio API HTTP error", extra={"call_id": request.call_id})
            raise CallInitiationError(
                message=str(exc),
                error_code="HTTP_ERROR",
                provider_response={},
            )

    def parse_webhook_event(
        self,
        payload: dict[str, Any],
    ) -> WebhookEvent:
        """Parse Twilio webhook payload into standardized WebhookEvent."""
        if "CallSid" not in payload:
            raise WebhookParseError(
                message="Missing CallSid in payload",
                error_code="MISSING_CALL_SID",
                provider_response=payload,
            )

        if "CallStatus" not in payload:
            raise WebhookParseError(
                message="Missing CallStatus in payload",
                error_code="MISSING_CALL_STATUS",
                provider_response=payload,
            )

        provider_call_id = str(payload["CallSid"])
        status = self._map_status(str(payload["CallStatus"]))

        status_to_event: dict[CallStatus, WebhookEventType] = {
            CallStatus.INITIATED: WebhookEventType.CALL_INITIATED,
            CallStatus.RINGING: WebhookEventType.CALL_RINGING,
            CallStatus.IN_PROGRESS: WebhookEventType.CALL_ANSWERED,
            CallStatus.COMPLETED: WebhookEventType.CALL_COMPLETED,
            CallStatus.FAILED: WebhookEventType.CALL_FAILED,
            CallStatus.BUSY: WebhookEventType.CALL_BUSY,
            CallStatus.NO_ANSWER: WebhookEventType.CALL_NO_ANSWER,
        }
        event_type = status_to_event.get(status, WebhookEventType.CALL_COMPLETED)

        call_id = payload.get("call_id") or payload.get("CallId")

        campaign_id = None
        contact_id = None

        return WebhookEvent(
            event_type=event_type,
            provider_call_id=provider_call_id,
            call_id=str(call_id) if call_id else None,
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=status,
            timestamp=datetime.now(timezone.utc),
            raw_payload=payload,
        )

    def verify_twilio_signature(
        self,
        url: str,
        params: dict[str, Any],
        signature: str,
    ) -> bool:
        """Verify Twilio request signature (optional helper)."""
        token = self._config.twilio_auth_token
        if not token:
            return False

        sorted_params = sorted((k, str(v)) for k, v in params.items())
        data = url + "".join(k + v for k, v in sorted_params)
        digest = hmac.new(token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).digest()
        expected = b64encode(digest).decode("utf-8")
        return hmac.compare_digest(expected, signature)
