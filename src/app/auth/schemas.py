"""
Pydantic schemas for authentication.

REQ-002: OIDC authentication integration
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: str = Field(..., description="Subject (user ID or OIDC sub)")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(..., description="Issued at time")
    type: Literal["access", "refresh"] = Field(..., description="Token type")
    user_id: UUID | None = Field(None, description="Internal user ID")
    email: str | None = Field(None, description="User email")
    role: str | None = Field(None, description="User role")


class UserProfile(BaseModel):
    """User profile response schema."""

    id: UUID = Field(..., description="User ID")
    oidc_sub: str = Field(..., description="OIDC subject identifier")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    role: Literal["admin", "campaign_manager", "viewer"] = Field(
        ..., description="User role"
    )
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: datetime = Field(..., description="Last update time")


class LoginResponse(BaseModel):
    """Login initiation response."""

    authorization_url: str = Field(..., description="URL to redirect user for OIDC login")
    state: str = Field(..., description="CSRF state parameter")


class AuthCallbackRequest(BaseModel):
    """OIDC callback request schema."""

    code: str = Field(..., description="Authorization code from IdP")
    state: str = Field(..., description="State parameter for CSRF validation")


class AuthCallbackResponse(BaseModel):
    """OIDC callback response with tokens."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user: UserProfile = Field(..., description="User profile information")


class RefreshTokenRequest(BaseModel):
    """Token refresh request schema."""

    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Token refresh response schema."""

    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class OIDCUserInfo(BaseModel):
    """OIDC UserInfo response schema."""

    sub: str = Field(..., description="Subject identifier")
    email: EmailStr | None = Field(None, description="User email")
    email_verified: bool | None = Field(None, description="Email verification status")
    name: str | None = Field(None, description="Full name")
    preferred_username: str | None = Field(None, description="Preferred username")
    given_name: str | None = Field(None, description="Given name")
    family_name: str | None = Field(None, description="Family name")


class OIDCTokenResponse(BaseModel):
    """OIDC token endpoint response."""

    access_token: str = Field(..., description="OIDC access token")
    token_type: str = Field(..., description="Token type")
    expires_in: int | None = Field(None, description="Expiration in seconds")
    refresh_token: str | None = Field(None, description="OIDC refresh token")
    id_token: str | None = Field(None, description="OIDC ID token")
    scope: str | None = Field(None, description="Granted scopes")