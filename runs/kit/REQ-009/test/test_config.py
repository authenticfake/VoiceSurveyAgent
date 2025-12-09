"""
Tests for telephony configuration.

REQ-009: Telephony provider adapter interface
"""

import os
from unittest.mock import patch

import pytest

from app.telephony.config import ProviderType, TelephonyConfig, get_telephony_config


class TestTelephonyConfig:
    """Tests for TelephonyConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = TelephonyConfig(
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )

        assert config.provider_type == ProviderType.TWILIO
        assert config.webhook_base_url == "http://localhost:8000"
        assert config.max_concurrent_calls == 10
        assert config.call_timeout_seconds == 60

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = TelephonyConfig(
            provider_type=ProviderType.MOCK,
            twilio_account_sid="AC_TEST",
            twilio_auth_token="test_token",
            twilio_from_number="+14155550000",
            webhook_base_url="https://api.example.com",
            max_concurrent_calls=20,
            call_timeout_seconds=120,
        )

        assert config.provider_type == ProviderType.MOCK
        assert config.twilio_account_sid == "AC_TEST"
        assert config.twilio_auth_token == "test_token"
        assert config.twilio_from_number == "+14155550000"
        assert config.webhook_base_url == "https://api.example.com"
        assert config.max_concurrent_calls == 20
        assert config.call_timeout_seconds == 120

    def test_get_webhook_url(self) -> None:
        """Test webhook URL generation."""
        config = TelephonyConfig(
            webhook_base_url="https://api.example.com",
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )

        url = config.get_webhook_url()
        assert url == "https://api.example.com/webhooks/telephony/events"

        custom_url = config.get_webhook_url("/custom/path")
        assert custom_url == "https://api.example.com/custom/path"

    def test_get_webhook_url_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from base URL."""
        config = TelephonyConfig(
            webhook_base_url="https://api.example.com/",
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )

        url = config.get_webhook_url()
        assert url == "https://api.example.com/webhooks/telephony/events"

    def test_max_concurrent_calls_validation(self) -> None:
        """Test max_concurrent_calls validation."""
        # Valid values
        config = TelephonyConfig(
            max_concurrent_calls=1,
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )
        assert config.max_concurrent_calls == 1

        config = TelephonyConfig(
            max_concurrent_calls=100,
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )
        assert config.max_concurrent_calls == 100

    def test_call_timeout_validation(self) -> None:
        """Test call_timeout_seconds validation."""
        # Valid values
        config = TelephonyConfig(
            call_timeout_seconds=10,
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )
        assert config.call_timeout_seconds == 10

        config = TelephonyConfig(
            call_timeout_seconds=300,
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )
        assert config.call_timeout_seconds == 300


class TestProviderType:
    """Tests for ProviderType enum."""

    def test_provider_types(self) -> None:
        """Test all provider types are defined."""
        assert ProviderType.TWILIO.value == "twilio"
        assert ProviderType.MOCK.value == "mock"


class TestGetTelephonyConfig:
    """Tests for get_telephony_config function."""

    def test_returns_config_instance(self) -> None:
        """Test that function returns TelephonyConfig instance."""
        config = get_telephony_config()
        assert isinstance(config, TelephonyConfig)