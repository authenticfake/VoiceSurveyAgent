"""
Telephony provider configuration.

REQ-009: Telephony provider adapter interface
- Adapter configurable via ProviderConfig entity

PATCH (Media Streams bootstrap, Phase 1):
- Introduce telephony_mode feature flag:
    legacy        -> existing TwiML/Gather-based flow (unchanged)
    media_streams -> /voice returns TwiML <Connect><Stream> (bootstrap only)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderType(str, Enum):
    """Supported telephony provider types."""

    TWILIO = "twilio"
    MOCK = "mock"


TelephonyMode = Literal["legacy", "media_streams"]


class TelephonyConfig(BaseSettings):
    """Telephony provider configuration from environment."""

    model_config = SettingsConfigDict(
        env_prefix="TELEPHONY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Provider selection
    provider_type: ProviderType = Field(default=ProviderType.TWILIO)

    # Provider credentials
    twilio_account_sid: str = Field(default="")
    twilio_auth_token: str = Field(default="")
    twilio_from_number: str = Field(default="")

    # Webhook base URL (HTTP) used for Twilio Call.Url and callbacks
    webhook_base_url: str = Field(default="http://localhost:8000")

    # Concurrency / timeouts
    max_concurrent_calls: int = Field(default=10, ge=1, le=100)
    call_timeout_seconds: int = Field(default=60, ge=10, le=300)

    # ---- NEW: Media Streams gating (bootstrap only in Patch 1)
    telephony_mode: TelephonyMode = Field(
        default="legacy",
        description="legacy|media_streams. Controls /voice response behavior.",
    )

    # Optional: explicit public base for WS (e.g. wss://<public-host>)
    # If empty, WS URL will be derived from PUBLIC_BASE_URL or request headers.
    media_streams_ws_public_url: str = Field(
        default="",
        description="Public WSS base URL for Twilio Media Streams (e.g. wss://xyz.ngrok.app).",
    )

    # Path on this FastAPI app where WS server will live (Patch 2 implements it)
    media_streams_ws_path: str = Field(
        default="/webhooks/telephony/streams",
        description="WebSocket path for Twilio Media Streams (Patch 2).",
    )

    def get_webhook_url(self, path: str = "/webhooks/telephony/events") -> str:
        base = self.webhook_base_url.rstrip("/")
        return f"{base}{path}"


def get_telephony_config() -> TelephonyConfig:
    return TelephonyConfig()


@dataclass(frozen=True)
class ProviderConfig:
    """ProviderConfig entity (in-memory representation).

    REQ-009 mentions a ProviderConfig entity. In the promoted codebase this may
    come from ORM/DB, but for logic and tests we keep a tiny in-memory model.
    """

    provider_type: ProviderType = ProviderType.TWILIO
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    webhook_base_url: str = "http://localhost:8000"
    max_concurrent_calls: int = 10
    call_timeout_seconds: int = 60

    # Keep feature flags available also for in-memory config if needed later
    telephony_mode: TelephonyMode = "legacy"
    media_streams_ws_public_url: str = ""
    media_streams_ws_path: str = "/webhooks/telephony/streams"


def config_from_provider_config(entity: ProviderConfig) -> TelephonyConfig:
    """Build TelephonyConfig from a ProviderConfig entity."""
    return TelephonyConfig(
        provider_type=entity.provider_type,
        twilio_account_sid=entity.twilio_account_sid,
        twilio_auth_token=entity.twilio_auth_token,
        twilio_from_number=entity.twilio_from_number,
        webhook_base_url=entity.webhook_base_url,
        max_concurrent_calls=entity.max_concurrent_calls,
        call_timeout_seconds=entity.call_timeout_seconds,
        telephony_mode=entity.telephony_mode,
        media_streams_ws_public_url=entity.media_streams_ws_public_url,
        media_streams_ws_path=entity.media_streams_ws_path,
    )