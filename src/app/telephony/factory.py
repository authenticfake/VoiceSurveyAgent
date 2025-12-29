"""
Telephony provider factory.

Single source of truth for configuration:
- use TelephonyConfig (Pydantic Settings) which loads from OS env + .env
- never read raw os.getenv("TWILIO_*") here
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.telephony.config import ProviderType, TelephonyConfig
from app.telephony.config import get_telephony_config as _get_settings_telephony_config
from app.telephony.interface import TelephonyProvider
from app.telephony.adapters.mock import MockTelephonyProvider
from app.telephony.twilio_adapter import TwilioAdapter

logger = logging.getLogger(__name__)


def _mask(s: str, keep: int = 6) -> str:
    if not s:
        return ""
    if len(s) <= keep:
        return "*" * len(s)
    return f"{s[:keep]}***"


@lru_cache(maxsize=1)
def get_telephony_config() -> TelephonyConfig:
    """
    Return cached TelephonyConfig loaded from OS env + .env (Pydantic Settings).
    This preserves the old import path: from app.telephony.factory import get_telephony_config
    """
    return _get_settings_telephony_config()


@lru_cache(maxsize=1)
def get_telephony_provider() -> TelephonyProvider:
    """
    Create and cache the telephony provider using TelephonyConfig.
    """
    cfg = get_telephony_config()

    logger.info(
        "Telephony config resolved",
        extra={
            "provider_type": getattr(cfg.provider_type, "value", str(cfg.provider_type)),
            "twilio_account_sid": _mask(cfg.twilio_account_sid),
            "twilio_from_number": cfg.twilio_from_number,
            "webhook_base_url": cfg.webhook_base_url,
            "max_concurrent_calls": cfg.max_concurrent_calls,
            "call_timeout_seconds": cfg.call_timeout_seconds,
        },
    )

    if cfg.provider_type == ProviderType.TWILIO:
        return TwilioAdapter(cfg)

    if cfg.provider_type == ProviderType.MOCK:
        return MockTelephonyProvider(cfg)

    raise ValueError(f"Unsupported telephony provider_type: {cfg.provider_type}")
