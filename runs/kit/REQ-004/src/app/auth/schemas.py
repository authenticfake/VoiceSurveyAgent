"""
Authentication schemas.

Pydantic models for authentication-related data structures.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"

class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: str = Field(..., description="Subject (OIDC subject identifier)")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(..., description="Issued at time")
    iss: str | None = Field(None, description="Issuer")
    aud: str | list[str] | None = Field(None, description="Audience")
    email: EmailStr | None = Field(None, description="User email")
    name: str | None = Field(None, description="User name")
    role: UserRole | None = Field(None, description="User role from claims")

class UserContext(BaseModel):
    """Current user context for request handling."""

    id: UUID = Field(..., description="User ID")
    oidc_sub: str = Field(..., description="OIDC subject identifier")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    role: UserRole = Field(..., description="User role")

    class Config:
        """Pydantic configuration."""

        from_attributes = True