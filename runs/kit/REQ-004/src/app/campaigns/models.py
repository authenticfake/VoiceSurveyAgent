"""
SQLAlchemy models for campaigns and users.

Defines ORM models that map to the database schema from REQ-001.
"""

from datetime import datetime, time
from enum import Enum as PyEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base

if TYPE_CHECKING:
    from app.campaigns.models import User

class UserRoleEnum(str, PyEnum):
    """User role enumeration matching database enum."""

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"

class CampaignStatusEnum(str, PyEnum):
    """Campaign status enumeration matching database enum."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CampaignLanguageEnum(str, PyEnum):
    """Campaign language enumeration matching database enum."""

    EN = "en"
    IT = "it"

class QuestionTypeEnum(str, PyEnum):
    """Question type enumeration matching database enum."""

    FREE_TEXT = "free_text"
    NUMERIC = "numeric"
    SCALE = "scale"

class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    oidc_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(UserRoleEnum, name="user_role", create_type=False),
        nullable=False,
        default=UserRoleEnum.VIEWER,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign",
        back_populates="created_by_user",
        lazy="selectin",
    )

class Campaign(Base):
    """Campaign model for survey campaigns."""

    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(CampaignStatusEnum, name="campaign_status", create_type=False),
        nullable=False,
        default=CampaignStatusEnum.DRAFT,
        index=True,
    )
    language: Mapped[str] = mapped_column(
        Enum(CampaignLanguageEnum, name="campaign_language", create_type=False),
        nullable=False,
        default=CampaignLanguageEnum.EN,
    )
    intro_script: Mapped[str] = mapped_column(Text, nullable=False)

    # Questions
    question_1_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_1_type: Mapped[str] = mapped_column(
        Enum(QuestionTypeEnum, name="question_type", create_type=False),
        nullable=False,
    )
    question_2_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_2_type: Mapped[str] = mapped_column(
        Enum(QuestionTypeEnum, name="question_type", create_type=False),
        nullable=False,
    )
    question_3_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_3_type: Mapped[str] = mapped_column(
        Enum(QuestionTypeEnum, name="question_type", create_type=False),
        nullable=False,
    )

    # Retry policy
    max_attempts: Mapped[int] = mapped_column(
        nullable=False,
        default=3,
    )
    retry_interval_minutes: Mapped[int] = mapped_column(
        nullable=False,
        default=60,
    )

    # Call time window
    allowed_call_start_local: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(9, 0),
    )
    allowed_call_end_local: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(20, 0),
    )

    # Email template references
    email_completed_template_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_refused_template_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_not_reached_template_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Creator reference
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    created_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="campaigns",
        lazy="selectin",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "max_attempts >= 1 AND max_attempts <= 5",
            name="check_max_attempts_range",
        ),
    )