"""
Telephony provider factory.

REQ-009: Telephony provider adapter interface
- Adapter configurable via ProviderConfig entity
"""

import logging
from typing import Any

from app.telephony.config import ProviderType, TelephonyConfig, get_telephony_config
from app.telephony.interface import TelephonyProvider
from app.telephony.mock_adapter import MockTelephonyAdapter
from app.telephony.twilio_adapter import TwilioAdapter

logger = logging.getLogger(__name__)

# Global provider instance for singleton pattern
_provider_instance: TelephonyProvider | None = None


def get_telephony_provider(
    config: TelephonyConfig | None = None,
    force_new: bool = False,
) -> TelephonyProvider:
    """Get telephony provider instance.

    Uses singleton pattern by default. Pass force_new=True to create
    a new instance.

    Args:
        config: Optional configuration override.
        force_new: If True, create new instance instead of using singleton.

    Returns:
        TelephonyProvider instance.
    """
    global _provider_instance

    if not force_new and _provider_instance is not None:
        return _provider_instance

    config = config or get_telephony_config()

    logger.info(
        "Creating telephony provider",
        extra={"provider_type": config.provider_type.value},
    )

    if config.provider_type == ProviderType.MOCK:
        provider = MockTelephonyAdapter()
    elif config.provider_type == ProviderType.TWILIO:
        provider = TwilioAdapter(config=config)
    else:
        # Default to Twilio
        provider = TwilioAdapter(config=config)

    if not force_new:
        _provider_instance = provider

    return provider


def reset_provider() -> None:
    """Reset the global provider instance.

    Useful for testing to ensure clean state.
    """
    global _provider_instance
    _provider_instance = None