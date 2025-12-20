"""
Twilio-compatible telephony provider adapter.

REQ-009: Telephony provider adapter interface
REQ-010: Telephony webhook handler
"""

import hashlib
import hmac
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx

from app.shared.logging import get_logger
from app.telephony.events import CallEvent, CallEventType
from app.telephony.interface import (
    CallInitiationRequest,
    CallInitiationResponse,
    TelephonyProvider,
    TelephonyProviderError,
)

logger = get_logger(__name__)

# Mapping from Twilio status to our domain event types
TWILIO_STATUS_MAP: dict[str, CallEventType] = {
    "queued": CallEventType.INITIATED,
    "initiated": CallEventType.INITIATED,
    "ringing": CallEventType.RINGING,
    "in-progress": CallEventType.ANSWERED,
    "completed": CallEventType.COMPLETED,
    "busy": CallEventType.BUSY,
    "no-answer": CallEventType.NO_ANSWER,
    "failed": CallEventType.FAILED,
    "canceled": CallEventType.FAILED,
}

class TwilioAdapter(TelephonyProvider):
    """Twilio-compatible telephony provider adapter.

    Implements the TelephonyProvider interface for Twilio's REST API
    and webhook format.
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        base_url: str = "https://api.twilio.com",
        timeout: float = 30.0,
    ) -> None:
        """Initialize Twilio adapter.

        Args:
            account_sid: Twilio account SID.
            auth_token: Twilio auth token.
            base_url: Twilio API base URL.
            timeout: HTTP request timeout in seconds.
        """
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._base_url = base_url
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                auth=(self._account_sid, self._auth_token),
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def initiate_call(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Initiate an outbound call via Twilio.

        Args:
            request: Call initiation request.

        Returns:
            Response with provider call ID.

        Raises:
            TelephonyProviderError: If call initiation fails.
        """
        client = await self._get_client()
        url = f"{self._base_url}/2010-04-01/Accounts/{self._account_sid}/Calls.json"

        # Build metadata to pass through status callbacks
        metadata = {
            "call_id": request.call_id,
            "campaign_id": str(request.campaign_id),
            "contact_id": str(request.contact_id),
            "language": request.language,
            **request.metadata,
        }

        form_data = {
            "To": request.to_number,
            "From": request.from_number,
            "StatusCallback": request.callback_url,
            "StatusCallbackMethod": "POST",
            "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"],
            # Pass metadata as URL parameters in callback
            "StatusCallback": f"{request.callback_url}?{urlencode(metadata)}",
        }

        logger.info(
            "Initiating Twilio call",
            extra={
                "call_id": request.call_id,
                "to": request.to_number,
                "campaign_id": str(request.campaign_id),
            },
        )

        try:
            response = await client.post(url, data=form_data)
            response.raise_for_status()
            data = response.json()

            return CallInitiationResponse(
                provider_call_id=data["sid"],
                status=data["status"],
                metadata={"raw_response": data},
            )

        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass

            logger.error(
                "Twilio call initiation failed",
                extra={
                    "call_id": request.call_id,
                    "status_code": e.response.status_code,
                    "error": error_data,
                },
            )
            raise TelephonyProviderError(
                message=f"Twilio API error: {e.response.status_code}",
                error_code=str(error_data.get("code", "unknown")),
                provider_response=error_data,
            ) from e

        except httpx.RequestError as e:
            logger.error(
                "Twilio request failed",
                extra={"call_id": request.call_id, "error": str(e)},
            )
            raise TelephonyProviderError(
                message=f"Twilio request failed: {e}",
            ) from e

    def parse_webhook_event(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> CallEvent:
        """Parse Twilio webhook payload into domain CallEvent.

        Args:
            payload: Twilio webhook form data as dict.
            headers: HTTP headers (for signature validation).

        Returns:
            Parsed CallEvent.

        Raises:
            ValueError: If required fields are missing.
        """
        # Extract required fields
        provider_call_id = payload.get("CallSid")
        if not provider_call_id:
            raise ValueError("Missing CallSid in webhook payload")

        call_status = payload.get("CallStatus", "").lower()
        event_type = TWILIO_STATUS_MAP.get(call_status)
        if event_type is None:
            logger.warning(
                "Unknown Twilio call status",
                extra={"status": call_status, "call_sid": provider_call_id},
            )
            event_type = CallEventType.FAILED

        # Extract metadata from query parameters or payload
        call_id = payload.get("call_id")
        campaign_id_str = payload.get("campaign_id")
        contact_id_str = payload.get("contact_id")

        if not all([call_id, campaign_id_str, contact_id_str]):
            raise ValueError(
                "Missing required metadata (call_id, campaign_id, contact_id)"
            )

        try:
            campaign_id = UUID(campaign_id_str)
            contact_id = UUID(contact_id_str)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid UUID in metadata: {e}") from e

        # Extract optional fields
        duration_str = payload.get("CallDuration")
        duration_seconds = int(duration_str) if duration_str else None

        error_code = payload.get("ErrorCode")
        error_message = payload.get("ErrorMessage")

        # Build timestamp
        timestamp = datetime.utcnow()

        return CallEvent(
            event_type=event_type,
            call_id=call_id,
            provider_call_id=provider_call_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            timestamp=timestamp,
            duration_seconds=duration_seconds,
            error_code=error_code,
            error_message=error_message,
            raw_status=call_status,
            metadata={
                "from": payload.get("From"),
                "to": payload.get("To"),
                "direction": payload.get("Direction"),
                "answered_by": payload.get("AnsweredBy"),
            },
        )

    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        url: str | None = None,
    ) -> bool:
        """Validate Twilio webhook signature.

        Twilio uses HMAC-SHA1 for signature validation.

        Args:
            payload: Raw request body.
            signature: X-Twilio-Signature header value.
            url: Full request URL.

        Returns:
            True if signature is valid.
        """
        if not url:
            logger.warning("URL required for Twilio signature validation")
            return False

        # Twilio signature is computed over URL + sorted POST params
        # For simplicity, we'll validate using the auth token
        try:
            # Parse form data from payload
            from urllib.parse import parse_qs

            params = parse_qs(payload.decode("utf-8"))
            # Flatten single-value lists
            flat_params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

            # Build signature string: URL + sorted params
            signature_string = url
            for key in sorted(flat_params.keys()):
                signature_string += key + str(flat_params[key])

            # Compute expected signature
            expected = hmac.new(
                self._auth_token.encode("utf-8"),
                signature_string.encode("utf-8"),
                hashlib.sha1,
            ).digest()

            import base64

            expected_b64 = base64.b64encode(expected).decode("utf-8")

            return hmac.compare_digest(expected_b64, signature)

        except Exception as e:
            logger.error(
                "Signature validation error",
                extra={"error": str(e)},
            )
            return False