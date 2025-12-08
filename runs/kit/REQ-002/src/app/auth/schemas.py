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
    """JWT token payload after validation."""

    model_config = ConfigDict(frozen=True)

    sub: str = Field(..., description="Subject (OIDC user ID)")
    email: EmailStr | None = Field(None, description="User email")
    name: str | None = Field(None, description="User display name")
    exp: datetime = Field(..., description="Token expiration time")
    iat: datetime = Field(..., description="Token issued at time")
    iss: str = Field(..., description="Token issuer")
    aud: str | list[str] = Field(..., description="Token audience")


class UserContext(BaseModel):
    """Authenticated user context for request handling."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(..., description="Internal user ID")
    oidc_sub: str = Field(..., description="OIDC subject identifier")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    role: UserRole = Field(..., description="User role for RBAC")


class LoginResponse(BaseModel):
    """Response for login initiation."""

    authorization_url: HttpUrl = Field(..., description="URL to redirect for OIDC login")
    state: str = Field(..., description="CSRF state parameter")


class AuthenticatedResponse(BaseModel):
    """Response after successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    refresh_token: str | None = Field(None, description="Refresh token if available")
    user: UserContext = Field(..., description="Authenticated user context")


class RefreshRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str = Field(..., description="Refresh token")


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: UUID = Field(..., description="Internal user ID")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    role: UserRole = Field(..., description="User role")
    created_at: datetime = Field(..., description="Account creation time")