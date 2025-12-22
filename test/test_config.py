"""
Tests for telephony configuration.

REQ-009: Telephony provider adapter interface
"""

from app.telephony.config import (
    ProviderConfig,
    ProviderType,
    TelephonyConfig,
    config_from_provider_config,
    get_telephony_config,
)


class TestTelephonyConfig:
    def test_default_values(self) -> None:
        # TelephonyConfig extends BaseSettings: environment variables may override defaults.
        # To keep tests deterministic, we validate the declared default on the model field,
        # not the runtime value that can be affected by the user's environment.
        default = TelephonyConfig.model_fields["provider_type"].default
        assert default == ProviderType.TWILIO


    def test_custom_values(self) -> None:
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
        config = TelephonyConfig(
            webhook_base_url="https://api.example.com",
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )

        assert config.get_webhook_url() == "https://api.example.com/webhooks/telephony/events"
        assert config.get_webhook_url("/custom/path") == "https://api.example.com/custom/path"

    def test_get_webhook_url_strips_trailing_slash(self) -> None:
        config = TelephonyConfig(
            webhook_base_url="https://api.example.com/",
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )

        assert config.get_webhook_url() == "https://api.example.com/webhooks/telephony/events"


class TestProviderType:
    def test_provider_types(self) -> None:
        assert ProviderType.TWILIO.value == "twilio"
        assert ProviderType.MOCK.value == "mock"


class TestProviderConfigMapping:
    def test_config_from_provider_config(self) -> None:
        entity = ProviderConfig(
            provider_type=ProviderType.TWILIO,
            twilio_account_sid="AC_TEST",
            twilio_auth_token="test_token",
            twilio_from_number="+14155550000",
            webhook_base_url="https://example.com",
            max_concurrent_calls=5,
            call_timeout_seconds=45,
        )

        cfg = config_from_provider_config(entity)

        assert cfg.provider_type == ProviderType.TWILIO
        assert cfg.twilio_account_sid == "AC_TEST"
        assert cfg.twilio_auth_token == "test_token"
        assert cfg.twilio_from_number == "+14155550000"
        assert cfg.webhook_base_url == "https://example.com"
        assert cfg.max_concurrent_calls == 5
        assert cfg.call_timeout_seconds == 45


class TestGetTelephonyConfig:
    def test_returns_config_instance(self) -> None:
        config = get_telephony_config()
        assert isinstance(config, TelephonyConfig)
