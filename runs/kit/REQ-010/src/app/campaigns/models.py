"""
SQLAlchemy models for campaigns.

REQ-004: Campaign CRUD API
REQ-005: Campaign validation service
REQ-010: Telephony webhook handler (call_attempts relationship)
"""

from datetime import datetime, time
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import Base

if TYPE_CHECKING:
    from app.auth.models import User
    from app.calls.models import CallAttempt
    from app.contacts.models import Contact

class CampaignStatus(str, Enum):
    """Campaign lifecycle status."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CampaignLanguage(str, Enum):
    """Supported campaign languages."""

    EN = "en"
    IT = "it"

class QuestionType(str, Enum):
    """Survey question answer types."""

    FREE_TEXT = "free_text"
    NUMERIC = "numeric"
    SCALE = "scale"

class Campaign(Base):
    """Campaign model matching the database schema from REQ-001."""

    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[CampaignStatus] = mapped_column(
        SQLEnum(CampaignStatus, name="campaign_status", create_type=False),
        nullable=False,
        default=CampaignStatus.DRAFT,
        index=True,
    )
    language: Mapped[CampaignLanguage] = mapped_column(
        SQLEnum(CampaignLanguage, name="campaign_language", create_type=False),
        nullable=False,
        default=CampaignLanguage.EN,
    )
    intro_script: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    question_1_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    question_1_type: Mapped[QuestionType | None] = mapped_column(
        SQLEnum(QuestionType, name="question_type", create_type=False),
        nullable=True,
    )
    question_2_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    question_2_type: Mapped[QuestionType | None] = mapped_column(
        SQLEnum(QuestionType, name="question_type", create_type=False),
        nullable=True,
    )
    question_3_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    question_3_type: Mapped[QuestionType | None] = mapped_column(
        SQLEnum(QuestionType, name="question_type", create_type=False),
        nullable=True,
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    retry_interval_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )
    allowed_call_start_local: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )
    allowed_call_end_local: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    created_by: Mapped["User | None"] = relationship("User")
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    call_attempts: Mapped[list["CallAttempt"]] = relationship(
        "CallAttempt",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "max_attempts >= 1 AND max_attempts <= 5",
            name="check_max_attempts_range",
        ),
    )