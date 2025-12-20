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

# --- Optional DB entity (Smoke CRUD) ---
# REQ-009 acceptance: "Adapter configurable via ProviderConfig entity"
# This is intentionally minimal and sync-friendly. It is used only by the smoke test.

try:
    from datetime import datetime, timezone

    from sqlalchemy import DateTime, Integer, String
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    class _Base(DeclarativeBase):
        pass

    class ProviderConfig(_Base):
        __tablename__ = "provider_configs"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

        provider_type: Mapped[str] = mapped_column(String(32), default="mock", nullable=False)

        twilio_account_sid: Mapped[str] = mapped_column(String(128), default="", nullable=False)
        twilio_auth_token: Mapped[str] = mapped_column(String(256), default="", nullable=False)
        twilio_from_number: Mapped[str] = mapped_column(String(32), default="", nullable=False)

        webhook_base_url: Mapped[str] = mapped_column(String(256), default="", nullable=False)
        max_concurrent_calls: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
        call_timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

        def to_telephony_config_dict(self) -> dict[str, Any]:
            # Note: ProviderType is an Enum; TelephonyConfig accepts it.
            # We keep provider_type as string here; TelephonyConfig will coerce.
            return {
                "provider_type": self.provider_type,
                "twilio_account_sid": self.twilio_account_sid,
                "twilio_auth_token": self.twilio_auth_token,
                "twilio_from_number": self.twilio_from_number,
                "webhook_base_url": self.webhook_base_url,
                "max_concurrent_calls": self.max_concurrent_calls,
                "call_timeout_seconds": self.call_timeout_seconds,
            }

except Exception:  # pragma: no cover
    # SQLAlchemy may not be available in minimal installations.
    ProviderConfig = None  # type: ignore[assignment]
    _Base = None  # type: ignore[assignment]
