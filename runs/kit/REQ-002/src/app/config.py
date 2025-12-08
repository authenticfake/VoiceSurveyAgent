"""
Application configuration.

Centralized settings management using Pydantic Settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
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
    app_name: str = Field(default="voicesurveyagent", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: Literal["dev", "qa", "uat", "prod"] = Field(
        default="dev",
        description="Deployment environment",
    )

    # Database
    database_url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection URL",
    )
    database_pool_size: int = Field(default=5, description="Database pool size")
    database_max_overflow: int = Field(default=10, description="Database max overflow")

    # Redis
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # OIDC Configuration
    oidc_issuer: str | None = Field(
        None,
        description="OIDC issuer URL (e.g., https://auth.example.com)",
    )
    oidc_client_id: str = Field(
        default="voicesurveyagent",
        description="OIDC client ID",
    )
    oidc_client_secret: str = Field(
        default="",
        description="OIDC client secret",
    )
    oidc_redirect_uri: str = Field(
        default="http://localhost:8000/api/auth/callback",
        description="OIDC redirect URI",
    )

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="change-me-in-production-use-secrets-manager",
        description="JWT signing secret key",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(
        default=60,
        description="JWT expiration time in minutes",
    )
    jwt_issuer: str = Field(
        default="voicesurveyagent",
        description="JWT issuer claim",
    )
    jwt_audience: str = Field(
        default="voicesurveyagent-api",
        description="JWT audience claim",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: Literal["json", "console"] = Field(
        default="json",
        description="Log format",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()