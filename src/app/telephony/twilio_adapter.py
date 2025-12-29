from __future__ import annotations

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
from httpx import HTTPStatusError



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
                # NEW: single-flow voice webhook (deterministic)
        # We pass call_id/campaign_id/contact_id in query string so /voice can resolve state
        voice_url = (
            f"{self._config.webhook_base_url}/webhooks/telephony/voice"
            f"?call_id={request.call_id}"
            f"&campaign_id={request.campaign_id}"
            f"&contact_id={request.contact_id}"
        )

        payload = {
            "To": request.to,
            "From": request.from_number,
            "StatusCallback": request.callback_url,
            "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"],
            "StatusCallbackMethod": "POST",
            "Url": voice_url,
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


            if not call_id:
                logger.warning(
                    "Twilio webhook missing correlation call_id in payload",
                    extra={
                        "provider_call_id": call_sid,
                        "call_status": call_status,
                        "payload_keys": sorted(list(payload.keys())),
                    },
                )
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

from typing import Any

import httpx

from app.calls.repository import CallAttemptRepository
from app.shared.database import db_manager
from app.shared.logging import get_logger
from app.telephony.config import TelephonyConfig

logger = get_logger(__name__)

# BEGIN FILE: src/app/telephony/twilio_adapter.py

# ... (file invariato sopra)

class TwilioTelephonyControl:
    """
    Twilio implementation of the dialogue TelephonyControlProtocol (production).

    Design:
    - play_text/hangup do NOT return TwiML directly.
    - They persist a "next_tts" payload on CallAttempt.extra_metadata.
    - Then they REST-update the live Twilio call to fetch /webhooks/telephony/twiml.
    """

    TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

    def __init__(self, config: TelephonyConfig) -> None:
        self._config = config

        # Backward-compat: some older code might reference these attrs.
        self._account_sid = config.twilio_account_sid
        self._auth_token = config.twilio_auth_token

    async def _resolve_provider_call_id(self, internal_call_id: str) -> str | None:
        async with db_manager.session_factory() as session:
            repo = CallAttemptRepository(session)
            attempt = await repo.get_by_call_id(internal_call_id)
            if attempt is None:
                return None
            return attempt.provider_call_id

    async def _set_next_tts(self, internal_call_id: str, payload: dict[str, Any]) -> None:
        async with db_manager.session_factory() as session:
            repo = CallAttemptRepository(session)
            attempt = await repo.get_by_call_id(internal_call_id)
            if attempt is None:
                return
            meta = getattr(attempt, "extra_metadata", None) or getattr(attempt, "call_metadata", None) or {}
            meta["twilio_next_tts"] = payload
            await repo.update_extra_metadata(attempt.id, meta)
            await session.commit()

    def _build_twiml_url(self) -> str:
        base = (self._config.webhook_base_url or "").rstrip("/")
        if not base:
            raise ValueError("TelephonyConfig.webhook_base_url is required to build TwiML URL")
        return f"{base}/webhooks/telephony/twiml"

    async def _twilio_call_redirect_to_twiml(self, provider_call_id: str, call_id: str) -> None:
        twiml_url = self._build_twiml_url()
        base = self.TWILIO_API_BASE
        sid = self._config.twilio_account_sid
        auth = (self._config.twilio_account_sid, self._config.twilio_auth_token)

        call_url = f"{base}/Accounts/{sid}/Calls/{provider_call_id}.json"

        logger.info(
            "Redirecting call to TwiML",
            extra={"provider_call_id": provider_call_id, "twiml_url": twiml_url},
        )

        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            # 1) PRE-FLIGHT: read call status
            status_resp = await client.get(call_url, auth=auth, headers={"Accept": "application/json"})

            if status_resp.status_code >= 400:
                logger.error(
                    "Twilio call status lookup failed",
                    extra={
                        "status_code": status_resp.status_code,
                        "resp_text": status_resp.text,
                        "provider_call_id": provider_call_id,
                        "call_url": call_url,
                    },
                )
                return

            try:
                call_status = (status_resp.json() or {}).get("status", "")
            except Exception:
                logger.error(
                    "Twilio call status parse failed",
                    extra={"resp_text": status_resp.text, "provider_call_id": provider_call_id},
                )
                return

            if call_status != "in-progress":
                logger.warning(
                    "Skip redirect: call not in-progress",
                    extra={
                        "call_id": call_id,
                        "provider_call_id": provider_call_id,
                        "call_status": call_status,
                        "twiml_url": twiml_url,
                    },
                )
                return

            # 2) UPDATE: redirect to TwiML
            logger.info(
                "Redirecting live call to TwiML",
                extra={"call_id": call_id, "provider_call_id": provider_call_id, "twiml_url": twiml_url},
            )
            update_data = {"Url": twiml_url, "Method": "POST"}
            update_resp = await client.post(
                call_url,
                data=update_data,  # form-encoded
                auth=auth,
                headers={"Accept": "application/json"},
            )

        if update_resp.status_code >= 400:
            logger.error(
                "Twilio call redirect failed",
                extra={
                    "status_code": update_resp.status_code,
                    "resp_text": update_resp.text,
                    "provider_call_id": provider_call_id,
                    "twiml_url": twiml_url,
                    "call_url": call_url,
                },
            )
            return

        logger.info(
            "Twilio call redirect OK",
            extra={"provider_call_id": provider_call_id, "twiml_url": twiml_url},
        )

        

    async def play_text(self, call_id: str, text: str, language: str) -> None:
        provider_call_id = await self._resolve_provider_call_id(call_id)
        if provider_call_id:
             logger.debug(
                 "TwilioTelephonyControl: resolved provider_call_id",
                 extra={"call_id": call_id, "provider_call_id": provider_call_id},
             )
        if not provider_call_id:
            logger.warning(
                "TwilioTelephonyControl: provider_call_id not found",
                extra={"call_id": call_id},
            )
            return

        await self._set_next_tts(
            call_id,
            {"type": "say_and_gather", "text": text, "language": language},
        )

        await self._twilio_call_redirect_to_twiml(provider_call_id, call_id)

    async def hangup(self, call_id: str) -> None:
        provider_call_id = await self._resolve_provider_call_id(call_id)
        if not provider_call_id:
            logger.warning(
                "TwilioTelephonyControl: provider_call_id not found",
                extra={"call_id": call_id},
            )
            return

        auth = (self._config.twilio_account_sid, self._config.twilio_auth_token)
        data = {"Status": "completed"}
        url = (
            f"{self.TWILIO_API_BASE}/Accounts/"
            f"{self._config.twilio_account_sid}/Calls/{provider_call_id}.json"
        )

        async with httpx.AsyncClient(timeout=self._config.call_timeout_seconds) as client:
            resp = await client.post(url, data=data, auth=auth)

        resp.raise_for_status()

# END FILE

 