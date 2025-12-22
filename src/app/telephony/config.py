"""
Telephony provider configuration.

REQ-009: Telephony provider adapter interface
- Adapter configurable via ProviderConfig entity
"""

from dataclasses import dataclass
from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderType(str, Enum):
    """Supported telephony provider types."""

    TWILIO = "twilio"
    MOCK = "mock"


class TelephonyConfig(BaseSettings):
    """Telephony provider configuration from environment."""

    model_config = SettingsConfigDict(
        env_prefix="TELEPHONY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider_type: ProviderType = Field(default=ProviderType.TWILIO)
    twilio_account_sid: str = Field(default="")
    twilio_auth_token: str = Field(default="")
    twilio_from_number: str = Field(default="")
    webhook_base_url: str = Field(default="http://localhost:8000")
    max_concurrent_calls: int = Field(default=10, ge=1, le=100)
    call_timeout_seconds: int = Field(default=60, ge=10, le=300)

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
    )
