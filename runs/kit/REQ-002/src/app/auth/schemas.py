"""
Authentication schemas.

Pydantic models for OIDC and JWT authentication.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class UserRole(str, Enum):
    """User role enumeration matching database enum."""

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"


class OIDCConfig(BaseModel):
    """OIDC provider configuration."""

    model_config = ConfigDict(frozen=True)

    issuer: HttpUrl = Field(..., description="OIDC issuer URL")
    authorization_endpoint: HttpUrl = Field(..., description="Authorization endpoint")
    token_endpoint: HttpUrl = Field(..., description="Token endpoint")
    userinfo_endpoint: HttpUrl = Field(..., description="UserInfo endpoint")
    jwks_uri: HttpUrl = Field(..., description="JWKS URI for token validation")
    client_id: str = Field(..., description="OIDC client ID")
    client_secret: str = Field(..., description="OIDC client secret")
    redirect_uri: HttpUrl = Field(..., description="OAuth redirect URI")
    scopes: list[str] = Field(
        default=["openid", "profile", "email"],
        description="OAuth scopes to request",
    )


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    model_config = ConfigDict(frozen=True)

    sub: str = Field(..., description="Subject (OIDC subject identifier)")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(..., description="Issued at time")
    iss: str | None = Field(None, description="Issuer")
    aud: str | list[str] | None = Field(None, description="Audience")
    email: EmailStr | None = Field(None, description="User email")
    name: str | None = Field(None, description="User name")
    role: UserRole | None = Field(None, description="User role from claims")


class TokenResponse(BaseModel):
    """OAuth token response schema."""

    model_config = ConfigDict(frozen=True)

    access_token: str = Field(..., description="Access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    refresh_token: str | None = Field(None, description="Refresh token")
    id_token: str | None = Field(None, description="OIDC ID token")
    scope: str | None = Field(None, description="Granted scopes")


class UserContext(BaseModel):
    """Current user context for request handling."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(..., description="User ID")
    oidc_sub: str = Field(..., description="OIDC subject identifier")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    role: UserRole = Field(..., description="User role")


class LoginRequest(BaseModel):
    """Login initiation request."""

    redirect_url: HttpUrl | None = Field(
        None,
        description="URL to redirect after successful login",
    )


class LoginResponse(BaseModel):
    """Login initiation response."""

    authorization_url: HttpUrl = Field(..., description="URL to redirect for OIDC login")
    state: str = Field(..., description="OAuth state parameter")


class CallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="OAuth state parameter")


class AuthenticatedResponse(BaseModel):
    """Response after successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    refresh_token: str | None = Field(None, description="Refresh token for renewal")
    user: UserContext = Field(..., description="Authenticated user context")


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., description="Refresh token")


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: UUID = Field(..., description="User ID")
    oidc_sub: str = Field(..., description="OIDC subject identifier")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    role: UserRole = Field(..., description="User role")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")