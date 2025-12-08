import os

from app.infra.config import get_app_settings, reset_settings_cache


def test_env_settings_parsed(monkeypatch):
    monkeypatch.setenv("APP__DATABASE__URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv(
        "APP__MESSAGING__QUEUE_URL",
        "https://sqs.eu-central-1.amazonaws.com/123/survey-events.fifo",
    )
    monkeypatch.setenv("APP__MESSAGING__REGION_NAME", "eu-central-1")
    monkeypatch.setenv("APP__MESSAGING__FIFO", "true")
    monkeypatch.setenv("APP__PROVIDER__OUTBOUND_NUMBER", "+12065550123")
    monkeypatch.setenv(
        "APP__SCHEDULER__FACTORY_PATH", "test.fixtures.dummy_scheduler_impl:build_scheduler"
    )
    monkeypatch.setenv(
        "APP__EMAIL_WORKER__HANDLER_FACTORY_PATH",
        "test.fixtures.dummy_email_handler:build_handler",
    )

    reset_settings_cache()
    settings = get_app_settings()

    assert settings.database.url.endswith("/db")
    assert settings.messaging.fifo is True
    assert settings.provider.outbound_number == "+12065550123"
    assert settings.scheduler.factory_path.endswith("build_scheduler")
    assert settings.email_worker.max_number_of_messages == 5