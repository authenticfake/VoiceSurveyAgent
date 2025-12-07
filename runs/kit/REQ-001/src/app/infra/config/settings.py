from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized application configuration loaded from environment variables."""

    app_name: str = Field(default="voicesurveyagent", alias="APP_NAME")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./.tmp/auth.db", alias="DATABASE_URL"
    )
    oidc_client_id: str = Field(default="local-client", alias="OIDC_CLIENT_ID")
    oidc_client_secret: SecretStr = Field(
        default=SecretStr("local-secret"), alias="OIDC_CLIENT_SECRET"
    )
    oidc_authorization_url: str = Field(
        default="https://example-idp.test/oauth2/v1/authorize",
        alias="OIDC_AUTHORIZATION_URL",
    )
    oidc_token_url: str = Field(
        default="https://example-idp.test/oauth2/v1/token",
        alias="OIDC_TOKEN_URL",
    )
    oidc_jwks_url: str = Field(
        default="https://example-idp.test/oauth2/v1/keys", alias="OIDC_JWKS_URL"
    )
    oidc_issuer: str = Field(
        default="https://example-idp.test/", alias="OIDC_ISSUER"
    )
    oidc_default_scopes: List[str] = Field(
        default_factory=lambda: ["openid", "profile", "email"],
        alias="OIDC_DEFAULT_SCOPES",
    )
    oidc_role_claim: str = Field(default="roles", alias="OIDC_ROLE_CLAIM")
    http_timeout_seconds: float = Field(default=5.0, alias="HTTP_TIMEOUT_SECONDS")
    app_jwt_secret: SecretStr = Field(
        default=SecretStr("change-me"), alias="APP_JWT_SECRET"
    )
    app_jwt_algorithm: str = Field(default="HS256", alias="APP_JWT_ALGORITHM")
    app_jwt_expires_seconds: int = Field(
        default=3600, alias="APP_JWT_EXPIRES_SECONDS"
    )
    rbac_role_priority: List[str] = Field(
        default_factory=lambda: ["admin", "campaign_manager", "viewer"],
        alias="RBAC_ROLE_PRIORITY",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Memoized settings accessor."""
    return Settings()


def reload_settings() -> Settings:
    """Utility for tests to refresh settings cache."""
    cache = get_settings
    cache.cache_clear()
    return get_settings()