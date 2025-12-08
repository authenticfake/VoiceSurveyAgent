from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    """Database connection configuration."""

    url: str = Field(..., description="SQLAlchemy-compatible database URL.")


class MessagingSettings(BaseModel):
    """Settings for the survey event queue (SQS for slice-1)."""

    queue_url: str = Field(..., description="Full SQS queue URL.")
    region_name: str = Field(..., description="AWS region hosting the queue.")
    fifo: bool = Field(False, description="Whether the queue is FIFO.")
    access_key_id: str | None = Field(
        default=None, description="Optional access key (otherwise use IAM role)."
    )
    secret_access_key: str | None = Field(
        default=None, description="Optional secret access key."
    )
    session_token: str | None = Field(
        default=None, description="Optional session token for assumed roles."
    )
    message_group_id: str | None = Field(
        default="survey-events",
        description="Default message group for FIFO topics (ignored for standard).",
    )


class ProviderSettings(BaseModel):
    """Core telephony + LLM provider configuration."""

    provider_type: Literal["telephony_api", "voice_ai_platform"] = "telephony_api"
    provider_name: str = Field("twilio", description="Human readable provider label.")
    outbound_number: str = Field(..., description="Caller ID / outbound number.")
    max_concurrent_calls: PositiveInt = Field(
        10, description="Upper bound on in-flight provider calls."
    )
    llm_provider: Literal["openai", "anthropic", "azure-openai", "google"] = "openai"
    llm_model: str = Field("gpt-4.1-mini", description="Model identifier for gateway.")


class SchedulerSettings(BaseModel):
    """Dynamic loader info for the scheduler runnable."""

    factory_path: str = Field(
        ...,
        description="Import path to a callable returning a SchedulerRunnable "
        "(e.g. app.calling.scheduler.service:build_scheduler).",
    )
    poll_interval_seconds: PositiveInt = Field(
        30, description="Delay between scheduler cycles in seconds."
    )


class EmailWorkerSettings(BaseModel):
    """Email worker behaviour knobs and handler wiring."""

    handler_factory_path: str = Field(
        ...,
        description="Import path to callable returning EmailEventHandler "
        "(e.g. app.notifications.email.worker:build_handler).",
    )
    long_poll_seconds: int = Field(
        20,
        ge=0,
        le=20,
        description="SQS long-poll duration per receive call.",
    )
    visibility_timeout_seconds: PositiveInt = Field(
        60, description="SQS visibility timeout for in-flight messages."
    )
    max_number_of_messages: int = Field(
        5,
        ge=1,
        le=10,
        description="Batch size per SQS receive call.",
    )


class ObservabilitySettings(BaseModel):
    """Logging / tracing configuration."""

    log_level: str = Field(
        "INFO", description="Root logging level (DEBUG, INFO, etc.)."
    )
    service_name: str = Field(
        "voicesurveyagent", description="Service name injected in log records."
    )


class AppSettings(BaseSettings):
    """Full application configuration with nested models."""

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_nested_delimiter="__", case_sensitive=False
    )

    environment: str = Field("dev", description="Deployment environment label.")
    database: DatabaseSettings
    messaging: MessagingSettings
    provider: ProviderSettings
    scheduler: SchedulerSettings
    email_worker: EmailWorkerSettings
    observability: ObservabilitySettings = ObservabilitySettings()


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """Return cached application settings (loads env on first call)."""
    return AppSettings()  # type: ignore[call-arg]


def reset_settings_cache() -> None:
    """Clear cached settings (useful for tests)."""
    get_app_settings.cache_clear()  # type: ignore[attr-defined]