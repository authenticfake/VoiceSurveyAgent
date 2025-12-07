from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class Role(str, Enum):
    """System-supported RBAC roles."""

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"

    @classmethod
    def from_claim(cls, claim: str) -> "Role | None":
        try:
            return cls(claim)
        except ValueError:
            return None


@dataclass(slots=True)
class UserProfile:
    """Domain representation of an authenticated user."""

    id: UUID
    oidc_sub: str
    email: str
    name: str
    role: Role
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class OidcProfile:
    """Subset of OIDC claims relevant for persistence."""

    sub: str
    email: str
    name: str
    role: Role


class UserORM(Base):
    """SQLAlchemy ORM model for users derived from OIDC login."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("oidc_sub", name="uq_users_oidc_sub"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    oidc_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role, name="role_enum"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_domain(self) -> UserProfile:
        return UserProfile(
            id=self.id,
            oidc_sub=self.oidc_sub,
            email=self.email,
            name=self.name,
            role=self.role,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def apply_profile(self, profile: OidcProfile) -> None:
        self.email = profile.email
        self.name = profile.name
        self.role = profile.role


def derive_role_from_claims(
    claims: dict[str, Any], role_claim_key: str, priority: list[str]
) -> Role:
    """Resolve a domain Role based on configured claim key and priority ordering."""
    raw_claim = claims.get(role_claim_key)
    ordered = raw_claim or []
    if isinstance(ordered, str):
        ordered = [ordered]
    if not isinstance(ordered, list):
        ordered = []
    normalized = [str(item).lower() for item in ordered]
    for candidate in priority:
        if candidate in normalized:
            resolved = Role.from_claim(candidate)
            if resolved:
                return resolved
    return Role.VIEWER