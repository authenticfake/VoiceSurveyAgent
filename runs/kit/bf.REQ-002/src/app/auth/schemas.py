"""Pydantic schemas for authentication."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.auth.models import UserRole

class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str = Field(min_length=1, max_length=255)

class UserCreate(UserBase):
    """Schema for creating a user."""

    oidc_sub: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.VIEWER

class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None

class UserProfile(UserBase):
    """User profile response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole
    created_at: datetime
    updated_at: datetime

class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None

class AuthCallbackRequest(BaseModel):
    """OAuth2 callback request schema."""

    code: str = Field(min_length=1)
    state: str = Field(min_length=1)

class AuthCallbackResponse(BaseModel):
    """OAuth2 callback response schema."""

    user: UserProfile
    tokens: TokenResponse

class AuthLoginResponse(BaseModel):
    """Login initiation response."""

    authorization_url: str
    state: str

class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str = Field(min_length=1)