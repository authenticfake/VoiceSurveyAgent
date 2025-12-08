"""SQLAlchemy models for authentication."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Base class for all models."""

    pass

class UserRole(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"

class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=func.uuid_generate_v4(),
    )
    oidc_sub: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        PgEnum(UserRole, name="user_role", create_type=False),
        nullable=False,
        default=UserRole.VIEWER,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"