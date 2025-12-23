"""
Application configuration with environment-driven settings.

REQ-002: OIDC authentication integration
"""

from functools import lru_cache
import os
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "voicesurveyagent"
    app_env: Literal["dev", "qa", "uat", "prod"] = "dev"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurveyag3ent",
        description="PostgreSQL connection URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # OIDC Configuration
    oidc_issuer_url: str = Field(
        default="http://localhost:8888/realms/VoiceSurveyAgent",
        description="OIDC Identity Provider issuer URL",
    )
    oidc_client_id: str = Field(
        default="voice-survey-agent",
        description="OIDC client ID",
    )
    oidc_client_secret: str = Field(
        default="",
        description="wQGovP2T32xHHGVwEzRO7M2WLcSBuBPl",
    )
    oidc_redirect_uri: str = Field(
        default="http://localhost:8880/api/auth/callback",
        description="OIDC redirect URI after authentication",
    )
    oidc_scopes: str = Field(
        default="openid profile email",
        description="Space-separated OIDC scopes",
    )

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="change-me-in-production-use-secrets-manager",
        description="Secret key for signing session JWTs",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        description="Access token expiration in minutes",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration in days",
    )

    # CORS
    cors_origins: str = Field(
        default="http://localhost:8880",
        description="Comma-separated list of allowed CORS origins",
    )
    # Scheduler (REQ-008 runtime wiring)
    scheduler_enabled: bool = Field(
        default=False,
        description="Enable background call scheduler loop at app startup.",
    )
    scheduler_interval_seconds: int = Field(
        default=60,
        ge=5,
        le=3600,
        description="Scheduler tick interval in seconds.",
    )
    scheduler_lock_key: str = Field(
        default="voicesurveyagent_scheduler_v1",
        description="Stable key used to derive the Postgres advisory lock id.",
    )

    @field_validator("oidc_scopes", mode="before")
    @classmethod
    def validate_scopes(cls, v: str) -> str:
        """Ensure openid scope is always present."""
        scopes = v.split() if isinstance(v, str) else v
        if "openid" not in scopes:
            scopes = ["openid"] + list(scopes)
        return " ".join(scopes)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def oidc_scopes_list(self) -> list[str]:
        """Parse OIDC scopes into a list."""
        return self.oidc_scopes.split()


# @lru_cache
# def get_settings() -> Settings:
#     """Get cached settings instance."""
#     return Settings()

def _get_settings_cached() -> Settings:
    return Settings()

def get_settings() -> Settings:
    # Sotto pytest, env var/monkeypatch cambiano durante i test:
    # non vogliamo una Settings “freezata” che rompe la firma JWT.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return Settings()
    return _get_settings_cached()
#