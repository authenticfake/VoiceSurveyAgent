# src/app/telephony/adapters/mock.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.telephony.interface import CallInfo, CallStatus, TelephonyProvider
from app.telephony.interface import TelephonyProvider, CallInfo




@dataclass
class MockTelephonyProvider(TelephonyProvider):
    """
    Mock provider per dev/test manuali.
    NON tocca Twilio, ma restituisce un CallInfo valido.
    """
  

    def initiate_call_sync(self, to_number: str, from_number: str, webhook_url: str, metadata: dict[str, Any] | None = None) -> CallInfo:
        # Simula immediatamente una call "queued"
        now = datetime.now(timezone.utc)
        return CallInfo(
            provider_call_id="MOCK_CALL_000001",
            status=CallStatus.queued,
            created_at=now,
            raw={"mock": True, "to": to_number, "from": from_number, "webhook_url": webhook_url, "metadata": metadata or {}},
        )

    async def initiate_call(self, to_number: str, from_number: str, webhook_url: str, metadata: dict[str, Any] | None = None) -> CallInfo:
        # riusa la sync (va benissimo per mock)
        return self.initiate_call_sync(to_number, from_number, webhook_url, metadata)
