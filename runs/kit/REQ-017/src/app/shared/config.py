"""
Application configuration management.

REQ-017: Campaign dashboard stats API
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/voicesurvey",
        description="PostgreSQL connection URL",
    )

    # Redis cache
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching",
    )
    stats_cache_ttl_seconds: int = Field(
        default=60,
        description="TTL for stats cache in seconds",
    )

    # Auth
    jwt_secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT validation",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")

    # OIDC
    oidc_issuer: str = Field(
        default="https://idp.example.com",
        description="OIDC issuer URL",
    )
    oidc_audience: str = Field(
        default="voicesurvey-api",
        description="OIDC audience",
    )

    # Observability
    log_level: str = Field(default="INFO", description="Log level")
    correlation_id_header: str = Field(
        default="X-Correlation-ID",
        description="Header name for correlation ID",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()