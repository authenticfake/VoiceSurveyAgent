"""
Telephony provider factory.

REQ-009: Telephony provider adapter interface
- Adapter configurable via ProviderConfig entity
"""

import logging

import httpx

from app.telephony.config import ProviderType, TelephonyConfig, get_telephony_config
from app.telephony.interface import TelephonyProvider
from app.telephony.mock_adapter import MockTelephonyAdapter
from app.telephony.twilio_adapter import TwilioAdapter

logger = logging.getLogger(__name__)

_provider_instance: TelephonyProvider | None = None


def get_telephony_provider(
    config: TelephonyConfig | None = None,
    force_new: bool = False,
    provider_override: TelephonyProvider | None = None,
    http_client: httpx.Client | None = None,
) -> TelephonyProvider:
    """Get telephony provider instance (singleton by default)."""
    global _provider_instance

    if not force_new and _provider_instance is not None:
        return _provider_instance

    if provider_override is not None:
        if not force_new:
            _provider_instance = provider_override
        return provider_override

    config = config or get_telephony_config()

    logger.info(
        "Creating telephony provider",
        extra={"provider_type": config.provider_type.value},
    )

    if config.provider_type == ProviderType.MOCK:
        provider = MockTelephonyAdapter()
    else:
        provider = TwilioAdapter(config=config, http_client=http_client)

    if not force_new:
        _provider_instance = provider

    return provider


def reset_provider() -> None:
    global _provider_instance
    _provider_instance = None
