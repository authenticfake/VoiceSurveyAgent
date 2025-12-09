"""
SQLAlchemy models for campaigns.

REQ-004: Campaign CRUD API
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


# Valid status transitions as per SPEC state machine
VALID_STATUS_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.DRAFT: {CampaignStatus.SCHEDULED, CampaignStatus.RUNNING, CampaignStatus.CANCELLED},
    CampaignStatus.SCHEDULED: {CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.CANCELLED},
    CampaignStatus.RUNNING: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
    CampaignStatus.PAUSED: {CampaignStatus.RUNNING, CampaignStatus.CANCELLED},
    CampaignStatus.COMPLETED: set(),  # Terminal state
    CampaignStatus.CANCELLED: set(),  # Terminal state
}


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
        SQLEnum(
            CampaignStatus,
            name="campaign_status",
            create_type=False,
        ),
        nullable=False,
        default=CampaignStatus.DRAFT,
        index=True,
    )
    language: Mapped[CampaignLanguage] = mapped_column(
        SQLEnum(
            CampaignLanguage,
            name="campaign_language",
            create_type=False,
        ),
        nullable=False,
        default=CampaignLanguage.EN,
    )
    intro_script: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # Question 1
    question_1_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    question_1_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(
            QuestionType,
            name="question_type",
            create_type=False,
        ),
        nullable=False,
    )
    
    # Question 2
    question_2_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    question_2_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(
            QuestionType,
            name="question_type",
            create_type=False,
        ),
        nullable=False,
    )
    
    # Question 3
    question_3_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    question_3_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(
            QuestionType,
            name="question_type",
            create_type=False,
        ),
        nullable=False,
    )
    
    # Retry policy
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
    
    # Call time window
    allowed_call_start_local: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    allowed_call_end_local: Mapped[time] = mapped_column(
        Time,
        nullable=False,
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
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "max_attempts >= 1 AND max_attempts <= 5",
            name="check_max_attempts_range",
        ),
        CheckConstraint(
            "retry_interval_minutes >= 1",
            name="check_retry_interval_positive",
        ),
        CheckConstraint(
            "allowed_call_start_local < allowed_call_end_local",
            name="check_call_window_valid",
        ),
    )

    def can_transition_to(self, new_status: CampaignStatus) -> bool:
        """Check if transition to new status is valid.

        Args:
            new_status: Target status to transition to.

        Returns:
            True if transition is valid, False otherwise.
        """
        return new_status in VALID_STATUS_TRANSITIONS.get(self.status, set())

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', status={self.status.value})>"