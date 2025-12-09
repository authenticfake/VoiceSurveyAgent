from __future__ import annotations

import functools
import os
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class OIDCSettings(BaseModel):
    issuer: str = Field(..., description="OIDC issuer base URL")
    client_id: str
    client_secret: str
    authorization_endpoint: HttpUrl
    token_endpoint: HttpUrl
    userinfo_endpoint: HttpUrl
    default_redirect_uri: HttpUrl
    scope: str = "openid profile email"


class TokenSettings(BaseModel):
    secret_key: str = Field(..., min_length=32)
    issuer: str = "voicesurveyagent"
    access_token_ttl_seconds: int = Field(300, ge=60, le=3600)
    refresh_token_ttl_seconds: int = Field(3600 * 24, ge=600, le=3600 * 24 * 30)


class AppSettings(BaseModel):
    environment: str = Field("dev", alias="ENVIRONMENT")
    database_url: str = Field(..., alias="DATABASE_URL")
    oidc: OIDCSettings
    tokens: TokenSettings
    http_timeout_seconds: float = Field(10, ge=1, le=60)

    class Config:
        populate_by_name = True


def build_settings() -> AppSettings:
    return AppSettings(
        database_url=os.environ["DATABASE_URL"],
        oidc=OIDCSettings(
            issuer=os.environ["OIDC_ISSUER"],
            client_id=os.environ["OIDC_CLIENT_ID"],
            client_secret=os.environ["OIDC_CLIENT_SECRET"],
            authorization_endpoint=os.environ["OIDC_AUTHORIZATION_ENDPOINT"],
            token_endpoint=os.environ["OIDC_TOKEN_ENDPOINT"],
            userinfo_endpoint=os.environ["OIDC_USERINFO_ENDPOINT"],
            default_redirect_uri=os.environ["OIDC_REDIRECT_URI"],
        ),
        tokens=TokenSettings(
            secret_key=os.environ["AUTH_TOKEN_SECRET"],
            issuer=os.environ.get("AUTH_TOKEN_ISSUER", "voicesurveyagent"),
            access_token_ttl_seconds=int(
                os.environ.get("ACCESS_TOKEN_TTL_SECONDS", "600")
            ),
            refresh_token_ttl_seconds=int(
                os.environ.get("REFRESH_TOKEN_TTL_SECONDS", str(3600 * 24))
            ),
        ),
        http_timeout_seconds=float(os.environ.get("HTTP_TIMEOUT_SECONDS", "10")),
    )


@functools.lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return build_settings()


def override_settings(settings: Optional[AppSettings]) -> None:
    get_settings.cache_clear()
    if settings is None:
        return
    get_settings.cache_clear()
    get_settings.cache_overrides = {(): settings}  # type: ignore[attr-defined]