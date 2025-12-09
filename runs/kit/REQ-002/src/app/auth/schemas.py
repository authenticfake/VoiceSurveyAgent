from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class LoginResponseUser(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: LoginResponseUser


class LoginRedirectResponse(BaseModel):
    authorization_url: HttpUrl
    state: str


class CallbackRequest(BaseModel):
    code: str
    redirect_uri: Optional[HttpUrl] = None
    state: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class SessionClaims(BaseModel):
    sub: UUID
    role: str
    type: str
    exp: datetime
    iat: datetime
    jti: str