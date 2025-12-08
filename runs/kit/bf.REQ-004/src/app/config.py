"""
Application configuration module.

Provides centralized configuration management using Pydantic Settings
with environment variable support.
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
    app_name: str = Field(default="VoiceSurveyAgent", description="Application name")
    app_env: Literal["dev", "qa", "uat", "prod"] = Field(
        default="dev", description="Application environment"
    )
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql://postgres:postgres@localhost:5432/voicesurvey",
        description="PostgreSQL connection URL",
    )
    database_pool_size: int = Field(default=5, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Max overflow connections")

    # Redis
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # Auth
    oidc_issuer_url: str = Field(
        default="https://auth.example.com",
        description="OIDC issuer URL",
    )
    oidc_client_id: str = Field(
        default="voicesurvey-client",
        description="OIDC client ID",
    )
    oidc_client_secret: str = Field(
        default="",
        description="OIDC client secret",
    )
    jwt_algorithm: str = Field(default="RS256", description="JWT algorithm")
    jwt_audience: str = Field(default="voicesurvey-api", description="JWT audience")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )

    # API
    api_prefix: str = Field(default="/api", description="API route prefix")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # Pagination
    default_page_size: int = Field(default=20, description="Default pagination size")
    max_page_size: int = Field(default=100, description="Maximum pagination size")

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()