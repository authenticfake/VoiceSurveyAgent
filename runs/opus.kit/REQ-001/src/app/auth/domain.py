"""Domain models for authentication and authorization."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"


class RBACPolicy:
    """Role-based access control policy definitions."""

    # Roles that can read campaigns, contacts, stats
    READ_ROLES: frozenset[UserRole] = frozenset(
        {UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER, UserRole.VIEWER}
    )

    # Roles that can create/update campaigns, upload contacts
    WRITE_ROLES: frozenset[UserRole] = frozenset(
        {UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER}
    )

    # Roles that can manage admin settings
    ADMIN_ROLES: frozenset[UserRole] = frozenset({UserRole.ADMIN})

    @classmethod
    def can_read(cls, role: UserRole) -> bool:
        """Check if role has read permissions."""
        return role in cls.READ_ROLES

    @classmethod
    def can_write(cls, role: UserRole) -> bool:
        """Check if role has write permissions."""
        return role in cls.WRITE_ROLES

    @classmethod
    def is_admin(cls, role: UserRole) -> bool:
        """Check if role has admin permissions."""
        return role in cls.ADMIN_ROLES


class User(BaseModel):
    """User domain model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    oidc_sub: str = Field(..., description="OIDC subject identifier")
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., description="Display name")
    role: UserRole = Field(default=UserRole.VIEWER, description="RBAC role")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class UserCreate(BaseModel):
    """Schema for creating a user from OIDC claims."""

    oidc_sub: str
    email: EmailStr
    name: str
    role: Optional[UserRole] = None


class UserUpdate(BaseModel):
    """Schema for updating user fields."""

    email: Optional[EmailStr] = None
    name: Optional[str] = None
    role: Optional[UserRole] = None


class UserResponse(BaseModel):
    """API response schema for user."""

    id: uuid.UUID
    email: EmailStr
    name: str
    role: UserRole
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True