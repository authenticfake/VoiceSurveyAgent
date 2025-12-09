"""
Tests for telephony provider factory.

REQ-009: Telephony provider adapter interface
"""

import pytest

from app.telephony.config import ProviderType, TelephonyConfig
from app.telephony.factory import get_telephony_provider, reset_provider
from app.telephony.mock_adapter import MockTelephonyAdapter
from app.telephony.twilio_adapter import TwilioAdapter


@pytest.fixture(autouse=True)
def reset_provider_singleton() -> None:
    """Reset provider singleton before each test."""
    reset_provider()


class TestGetTelephonyProvider:
    """Tests for get_telephony_provider factory function."""

    def test_get_twilio_provider(self) -> None:
        """Test getting Twilio provider."""
        config = TelephonyConfig(
            provider_type=ProviderType.TWILIO,
            twilio_account_sid="AC_TEST",
            twilio_auth_token="test_token",
            twilio_from_number="+14155550000",
        )

        provider = get_telephony_provider(config=config, force_new=True)

        assert isinstance(provider, TwilioAdapter)

    def test_get_mock_provider(self) -> None:
        """Test getting mock provider."""
        config = TelephonyConfig(
            provider_type=ProviderType.MOCK,
        )

        provider = get_telephony_provider(config=config, force_new=True)

        assert isinstance(provider, MockTelephonyAdapter)

    def test_singleton_pattern(self) -> None:
        """Test that factory returns same instance by default."""
        config = TelephonyConfig(
            provider_type=ProviderType.MOCK,
        )

        provider1 = get_telephony_provider(config=config)
        provider2 = get_telephony_provider(config=config)

        assert provider1 is provider2

    def test_force_new_creates_new_instance(self) -> None:
        """Test that force_new creates new instance."""
        config = TelephonyConfig(
            provider_type=ProviderType.MOCK,
        )

        provider1 = get_telephony_provider(config=config)
        provider2 = get_telephony_provider(config=config, force_new=True)

        assert provider1 is not provider2

    def test_reset_provider_clears_singleton(self) -> None:
        """Test that reset_provider clears singleton."""
        config = TelephonyConfig(
            provider_type=ProviderType.MOCK,
        )

        provider1 = get_telephony_provider(config=config)
        reset_provider()
        provider2 = get_telephony_provider(config=config)

        assert provider1 is not provider2