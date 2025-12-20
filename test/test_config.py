from __future__ import annotations

import os

import pytest

from app.telephony.config import ProviderType, TelephonyConfig, get_telephony_config


class TestTelephonyConfig:
    def test_default_values(self) -> None:
        config = TelephonyConfig(
            twilio_account_sid="",
            twilio_auth_token="",
            twilio_from_number="",
        )

        # We default to MOCK to keep safe/dev-first behaviour.
        assert config.provider_type == ProviderType.MOCK
        assert config.max_concurrent_calls >= 1
        assert config.call_timeout_seconds >= 1

    def test_from_env_mock(self, monkeypatch) -> None:
        monkeypatch.setenv("TELEPHONY_PROVIDER_TYPE", "mock")
        monkeypatch.setenv("TELEPHONY_TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setenv("TELEPHONY_TWILIO_AUTH_TOKEN", "secret")
        monkeypatch.setenv("TELEPHONY_TWILIO_FROM_NUMBER", "+15550001111")
        monkeypatch.setenv("TELEPHONY_WEBHOOK_BASE_URL", "https://example.test")
        monkeypatch.setenv("TELEPHONY_MAX_CONCURRENT_CALLS", "10")
        monkeypatch.setenv("TELEPHONY_CALL_TIMEOUT_SECONDS", "60")

        config = get_telephony_config()

        assert config.provider_type == ProviderType.MOCK
        assert config.twilio_account_sid == "AC123"
        assert config.webhook_base_url == "https://example.test"
        assert config.max_concurrent_calls == 10
        assert config.call_timeout_seconds == 60

    def test_from_env_twilio(self, monkeypatch) -> None:
        monkeypatch.setenv("TELEPHONY_PROVIDER_TYPE", "twilio")
        monkeypatch.setenv("TELEPHONY_TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setenv("TELEPHONY_TWILIO_AUTH_TOKEN", "secret")
        monkeypatch.setenv("TELEPHONY_TWILIO_FROM_NUMBER", "+15550001111")
        monkeypatch.setenv("TELEPHONY_WEBHOOK_BASE_URL", "https://example.test")

        config = get_telephony_config()
        assert config.provider_type == ProviderType.TWILIO
        assert config.twilio_from_number == "+15550001111"

    

    @pytest.mark.smoke
    def test_provider_config_entity_smoke_sqlite_roundtrip(self) -> None:
        sqlalchemy = pytest.importorskip("sqlalchemy")

        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from app.telephony.config import ProviderConfig, TelephonyConfig

        if ProviderConfig is None:
            pytest.skip("ProviderConfig entity not available (SQLAlchemy optional block disabled)")

        engine = create_engine("sqlite:///:memory:", future=True)

        # Create schema
        ProviderConfig.metadata.create_all(engine)

        # Insert + read back
        with Session(engine) as session:
            row = ProviderConfig(
                provider_type="twilio",
                twilio_account_sid="AC123",
                twilio_auth_token="secret",
                twilio_from_number="+15550001111",
                webhook_base_url="https://example.test",
                max_concurrent_calls=10,
                call_timeout_seconds=60,
            )
            session.add(row)
            session.commit()
            session.refresh(row)

            loaded = session.get(ProviderConfig, row.id)
            assert loaded is not None
            assert loaded.provider_type == "twilio"
            assert loaded.twilio_from_number == "+15550001111"

            # Entity -> runtime config mapping (adapter configurable via entity)
            cfg = TelephonyConfig(**loaded.to_telephony_config_dict())
            assert cfg.provider_type.value == "twilio"
            assert cfg.webhook_base_url == "https://example.test"
            assert cfg.max_concurrent_calls == 10
            assert cfg.call_timeout_seconds == 60

