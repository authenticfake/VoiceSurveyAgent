"""Application configuration with environment-driven settings."""

from functools import lru_cache
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
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey",
        description="PostgreSQL connection URL",
    )
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=10, ge=0, le=50)

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # OIDC Configuration
    oidc_issuer_url: str = Field(
        default="https://login.microsoftonline.com/common/v2.0",
        description="OIDC issuer URL for token validation",
    )
    oidc_client_id: str = Field(
        default="",
        description="OIDC client ID for this application",
    )
    oidc_client_secret: str = Field(
        default="",
        description="OIDC client secret",
    )
    oidc_redirect_uri: str = Field(
        default="http://localhost:8000/api/auth/callback",
        description="OAuth2 redirect URI after authentication",
    )
    oidc_scopes: str = Field(
        default="openid profile email",
        description="Space-separated OIDC scopes",
    )

    # JWT Configuration
    jwt_algorithm: str = "RS256"
    jwt_audience: str = Field(
        default="",
        description="Expected JWT audience claim",
    )
    jwt_access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    jwt_secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for signing session tokens",
    )

    # Session Configuration
    session_cookie_name: str = "voicesurvey_session"
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    @field_validator("oidc_scopes")
    @classmethod
    def validate_scopes(cls, v: str) -> str:
        """Ensure openid scope is always present."""
        scopes = v.split()
        if "openid" not in scopes:
            scopes.insert(0, "openid")
        return " ".join(scopes)

    @property
    def oidc_scopes_list(self) -> list[str]:
        """Return scopes as a list."""
        return self.oidc_scopes.split()

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()