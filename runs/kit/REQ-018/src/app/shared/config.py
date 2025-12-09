"""
Application configuration management.

REQ-018: Campaign CSV export
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey",
        description="PostgreSQL connection URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # AWS S3 Configuration
    aws_region: str = Field(default="eu-central-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    s3_bucket_name: str = Field(
        default="voicesurvey-exports",
        description="S3 bucket for CSV exports",
    )
    s3_export_prefix: str = Field(
        default="exports/",
        description="S3 prefix for export files",
    )
    export_url_expiration_seconds: int = Field(
        default=3600,
        description="Presigned URL expiration in seconds",
    )

    # OIDC Configuration
    oidc_issuer_url: str = Field(
        default="https://idp.example.com",
        description="OIDC issuer URL",
    )
    oidc_client_id: str = Field(default="voicesurvey", description="OIDC client ID")
    oidc_client_secret: str = Field(default="", description="OIDC client secret")
    oidc_audience: str = Field(default="voicesurvey-api", description="OIDC audience")

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="JWT signing secret",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60, description="JWT expiration in minutes")

    # Application
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    correlation_id_header: str = Field(
        default="X-Correlation-ID",
        description="Header name for correlation ID",
    )

    model_config = {"env_prefix": "", "case_sensitive": False, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()