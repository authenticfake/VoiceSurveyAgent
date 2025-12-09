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


# Mapping from Twilio call status to our CallStatus enum
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

# Mapping from Twilio status to webhook event type
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

    Implements the TelephonyProvider interface for Twilio's REST API.
    Uses httpx for async HTTP requests.
    """

    def __init__(
        self,
        config: TelephonyConfig | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize Twilio adapter.

        Args:
            config: Telephony configuration. Uses default if not provided.
            http_client: HTTP client for API calls. Creates new if not provided.
        """
        self._config = config or get_telephony_config()
        self._http_client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client.

        Returns:
            Async HTTP client.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client if owned by this adapter."""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _get_auth(self) -> tuple[str, str]:
        """Get HTTP basic auth credentials.

        Returns:
            Tuple of (account_sid, auth_token).
        """
        return (self._config.twilio_account_sid, self._config.twilio_auth_token)

    def _get_api_url(self, endpoint: str) -> str:
        """Get Twilio API URL.

        Args:
            endpoint: API endpoint path.

        Returns:
            Full API URL.
        """
        account_sid = self._config.twilio_account_sid
        return f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}{endpoint}"

    async def initiate_call(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Initiate an outbound call via Twilio.

        Args:
            request: Call initiation request.

        Returns:
            Response with Twilio call SID and status.

        Raises:
            CallInitiationError: If Twilio API call fails.
        """
        client = await self._get_client()

        # Build request payload
        # Using TwiML URL approach - Twilio will fetch TwiML from callback
        payload = {
            "To": request.to,
            "From": request.from_number,
            "StatusCallback": request.callback_url,
            "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"],
            "StatusCallbackMethod": "POST",
            # Store metadata in custom parameters for callback correlation
            "Url": f"{self._config.webhook_base_url}/webhooks/telephony/twiml",
            "Method": "POST",
        }

        # Add metadata as custom parameters (Twilio passes these back in callbacks)
        # Using SipHeader prefix for custom data
        metadata = {
            "call_id": request.call_id,
            "campaign_id": str(request.campaign_id),
            "contact_id": str(request.contact_id),
            "language": request.language,
            **request.metadata,
        }

        # Twilio supports custom parameters via the Url endpoint
        # We'll encode metadata in the callback URL as query params
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
            response = await client.post(
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

    def parse_webhook_event(
        self,
        payload: dict[str, Any],
    ) -> WebhookEvent:
        """Parse Twilio webhook event.

        Args:
            payload: Twilio webhook payload (form data as dict).

        Returns:
            Parsed webhook event.

        Raises:
            WebhookParseError: If payload is invalid.
        """
        try:
            # Extract required fields
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

            # Map status to event type
            event_type = TWILIO_EVENT_MAP.get(call_status)
            if event_type is None:
                # Default to completed for unknown statuses
                event_type = WebhookEventType.CALL_COMPLETED

            # Map status to CallStatus enum
            status = TWILIO_STATUS_MAP.get(call_status, CallStatus.COMPLETED)

            # Extract metadata from query params (passed via StatusCallback URL)
            call_id = payload.get("call_id")
            campaign_id_str = payload.get("campaign_id")
            contact_id_str = payload.get("contact_id")

            # Parse UUIDs
            from uuid import UUID

            campaign_id = UUID(campaign_id_str) if campaign_id_str else None
            contact_id = UUID(contact_id_str) if contact_id_str else None

            # Extract duration for completed calls
            duration_seconds = None
            if call_status == "completed" and payload.get("CallDuration"):
                try:
                    duration_seconds = int(payload["CallDuration"])
                except (ValueError, TypeError):
                    pass

            # Extract error info for failed calls
            error_code = None
            error_message = None
            if call_status == "failed":
                error_code = payload.get("ErrorCode")
                error_message = payload.get("ErrorMessage")

            # Parse timestamp
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

    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        url: str,
    ) -> bool:
        """Validate Twilio webhook signature.

        Twilio uses HMAC-SHA1 for signature validation.

        Args:
            payload: Raw request body bytes.
            signature: X-Twilio-Signature header value.
            url: Full URL that received the webhook.

        Returns:
            True if signature is valid.
        """
        if not self._config.twilio_auth_token:
            logger.warning("No auth token configured, skipping signature validation")
            return True

        try:
            # Twilio signature validation:
            # 1. Take the full URL
            # 2. Sort POST parameters alphabetically
            # 3. Append each parameter name and value to the URL
            # 4. HMAC-SHA1 with auth token
            # 5. Base64 encode

            # Parse form data from payload
            from urllib.parse import parse_qs

            params = parse_qs(payload.decode("utf-8"))

            # Build signature base string
            data_str = url
            for key in sorted(params.keys()):
                # parse_qs returns lists, take first value
                data_str += key + params[key][0]

            # Compute HMAC-SHA1
            computed = hmac.new(
                self._config.twilio_auth_token.encode("utf-8"),
                data_str.encode("utf-8"),
                hashlib.sha1,
            ).digest()

            computed_sig = b64encode(computed).decode("utf-8")

            return hmac.compare_digest(computed_sig, signature)

        except Exception as e:
            logger.exception("Error validating Twilio signature")
            return False