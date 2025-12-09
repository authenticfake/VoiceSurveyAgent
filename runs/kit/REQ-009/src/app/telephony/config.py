"""
Telephony provider configuration.

REQ-009: Telephony provider adapter interface
- Adapter configurable via ProviderConfig entity
"""

from enum import Enum
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderType(str, Enum):
    """Supported telephony provider types."""

    TWILIO = "twilio"
    MOCK = "mock"


class TelephonyConfig(BaseSettings):
    """Telephony provider configuration from environment.

    Attributes:
        provider_type: Type of telephony provider to use.
        twilio_account_sid: Twilio account SID.
        twilio_auth_token: Twilio auth token.
        twilio_from_number: Default outbound caller ID.
        webhook_base_url: Base URL for webhook callbacks.
        max_concurrent_calls: Maximum concurrent calls allowed.
        call_timeout_seconds: Timeout for call attempts.
    """

    model_config = SettingsConfigDict(
        env_prefix="TELEPHONY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider_type: ProviderType = Field(
        default=ProviderType.TWILIO,
        description="Telephony provider type",
    )
    twilio_account_sid: str = Field(
        default="",
        description="Twilio account SID",
    )
    twilio_auth_token: str = Field(
        default="",
        description="Twilio auth token",
    )
    twilio_from_number: str = Field(
        default="",
        description="Default outbound caller ID",
    )
    webhook_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for webhook callbacks",
    )
    max_concurrent_calls: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum concurrent calls",
    )
    call_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Call attempt timeout in seconds",
    )

    def get_webhook_url(self, path: str = "/webhooks/telephony/events") -> str:
        """Get full webhook URL.

        Args:
            path: Webhook endpoint path.

        Returns:
            Full webhook URL.
        """
        base = self.webhook_base_url.rstrip("/")
        return f"{base}{path}"


def get_telephony_config() -> TelephonyConfig:
    """Get telephony configuration singleton.

    Returns:
        TelephonyConfig instance.
    """
    return TelephonyConfig()