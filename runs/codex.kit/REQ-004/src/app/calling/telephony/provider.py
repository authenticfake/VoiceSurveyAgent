from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Protocol

import httpx

from app.calling.telephony.models import OutboundCallRequest, OutboundCallResponse

logger = logging.getLogger(__name__)


class TelephonyProviderError(RuntimeError):
    """Raised when the telephony provider cannot start a call."""


class TelephonyProvider(Protocol):
    """Interface every telephony adapter must implement."""

    def start_outbound_call(self, request: OutboundCallRequest) -> OutboundCallResponse: ...


@dataclass(frozen=True)
class TelephonyProviderSettings:
    """Adapter configuration injected from environment/secrets."""

    base_url: str
    api_key: str
    outbound_number: str
    callback_url: str
    timeout_seconds: float = 10.0


class HttpTelephonyProvider(TelephonyProvider):
    """
    Minimal HTTP adapter that posts outbound call requests to a REST provider.

    The adapter expects the provider to expose POST /calls that returns JSON
    containing "call_id" (provider identifier) and "status".
    """

    def __init__(
        self,
        settings: TelephonyProviderSettings,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=settings.timeout_seconds)

    def start_outbound_call(self, request: OutboundCallRequest) -> OutboundCallResponse:
        payload = {
            "to": request.to_number,
            "from": request.from_number or self._settings.outbound_number,
            "language": request.language,
            "callback_url": request.callback_url or self._settings.callback_url,
            "intro_script": request.intro_script,
            "questions": [
                {"position": q.position, "text": q.text, "answer_type": q.answer_type}
                for q in request.questions
            ],
            "metadata": request.metadata,
            "call_id": request.call_id,
        }
        headers = {"Authorization": f"Bearer {self._settings.api_key}"}
        try:
            response = self._client.post(f"{self._settings.base_url}/calls", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:  # ValueError for invalid JSON
            logger.error("Telephony provider call failed", exc_info=exc)
            raise TelephonyProviderError("Failed to start outbound call") from exc

        provider_call_id = data.get("call_id")
        status = data.get("status", "queued")
        if not provider_call_id:
            raise TelephonyProviderError("Provider response missing call_id")

        return OutboundCallResponse(
            provider_call_id=provider_call_id,
            provider_status=status,
            raw_payload=data,
        )

    def close(self) -> None:
        if self._client:
            self._client.close()