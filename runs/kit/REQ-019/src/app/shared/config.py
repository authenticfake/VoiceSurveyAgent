"""
Application configuration management.

REQ-019: Admin configuration API
"""

import os
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

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # AWS
    aws_region: str = Field(default="eu-central-1", description="AWS region")
    aws_secrets_manager_prefix: str = Field(
        default="voicesurvey", description="Prefix for secrets in AWS Secrets Manager"
    )

    # OIDC
    oidc_issuer_url: str = Field(
        default="https://idp.example.com", description="OIDC issuer URL"
    )
    oidc_client_id: str = Field(default="voicesurvey", description="OIDC client ID")
    oidc_audience: str = Field(default="voicesurvey-api", description="OIDC audience")

    # Application
    app_env: str = Field(default="development", description="Application environment")
    log_level: str = Field(default="INFO", description="Logging level")
    cors_origins: str = Field(default="*", description="CORS allowed origins")

    # Feature flags
    enable_audit_logging: bool = Field(
        default=True, description="Enable audit logging for admin actions"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()