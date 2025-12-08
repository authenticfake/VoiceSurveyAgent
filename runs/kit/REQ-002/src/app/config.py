"""
Application configuration.

Centralized settings management using Pydantic Settings.
"""

from functools import lru_cache

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
    app_env: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    database_url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection URL",
    )

    # Redis
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # OIDC Configuration
    oidc_issuer: str = Field(
        ...,
        description="OIDC issuer URL",
    )
    oidc_authorization_endpoint: str = Field(
        ...,
        description="OIDC authorization endpoint",
    )
    oidc_token_endpoint: str = Field(
        ...,
        description="OIDC token endpoint",
    )
    oidc_userinfo_endpoint: str = Field(
        ...,
        description="OIDC userinfo endpoint",
    )
    oidc_jwks_uri: str = Field(
        ...,
        description="OIDC JWKS URI",
    )
    oidc_client_id: str = Field(
        ...,
        description="OIDC client ID",
    )
    oidc_client_secret: str = Field(
        ...,
        description="OIDC client secret",
    )
    oidc_redirect_uri: str = Field(
        ...,
        description="OIDC redirect URI",
    )
    oidc_scopes: list[str] = Field(
        default=["openid", "profile", "email"],
        description="OIDC scopes",
    )

    # JWT Configuration
    jwt_algorithm: str = Field(default="RS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        description="Access token expiration in minutes",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration in days",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()