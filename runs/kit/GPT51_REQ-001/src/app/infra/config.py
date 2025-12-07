from __future__ import annotations

from functools import lru_cache
from pydantic import BaseSettings, AnyHttpUrl, Field


class Settings(BaseSettings):
    """Application configuration relevant for REQ‑001 (OIDC & API basics).

    Additional settings for other REQs can be added later in the same class.
    """

    app_name: str = "voicesurveyagent-api"
    environment: str = Field("dev", env="APP_ENV")

    # OIDC configuration
    oidc_issuer: str = Field(..., env="OIDC_ISSUER")
    oidc_client_id: str = Field(..., env="OIDC_CLIENT_ID")
    oidc_client_secret: str = Field(..., env="OIDC_CLIENT_SECRET")
    oidc_auth_endpoint: AnyHttpUrl = Field(..., env="OIDC_AUTH_ENDPOINT")
    oidc_token_endpoint: AnyHttpUrl = Field(..., env="OIDC_TOKEN_ENDPOINT")
    oidc_jwks_uri: AnyHttpUrl = Field(..., env="OIDC_JWKS_URI")
    oidc_redirect_uri: AnyHttpUrl = Field(..., env="OIDC_REDIRECT_URI")
    oidc_audience: str | None = Field(None, env="OIDC_AUDIENCE")
    oidc_scope: str = Field("openid profile email", env="OIDC_SCOPE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return singleton Settings instance for the process."""
    return Settings()