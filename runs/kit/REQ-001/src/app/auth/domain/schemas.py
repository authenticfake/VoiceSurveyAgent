from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from app.auth.domain.models import Role, UserProfile


class UserRead(BaseModel):
    id: str
    email: str
    name: str
    role: Role

    @classmethod
    def from_domain(cls, user: UserProfile) -> "UserRead":
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
        )


class OidcLoginResponse(BaseModel):
    authorization_url: str
    state: str
    nonce: str


class OidcCallbackRequest(BaseModel):
    code: str
    redirect_uri: str
    state: str | None = Field(default=None)
    nonce: str | None = Field(default=None)


class AuthTokensResponse(BaseModel):
    access_token: str
    refresh_token: str | None
    expires_in: int
    token_type: Literal["Bearer"] = "Bearer"
    id_token: str
    app_access_token: str
    user: UserRead


class ErrorResponse(BaseModel):
    error: str
    error_description: str