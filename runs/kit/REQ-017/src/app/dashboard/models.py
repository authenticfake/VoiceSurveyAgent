"""
Database models for dashboard queries.

REQ-017: Campaign dashboard stats API
"""

import enum
from datetime import datetime, time
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


class CampaignStatus(str, enum.Enum):
    """Campaign lifecycle status."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignLanguage(str, enum.Enum):
    """Supported campaign languages."""

    EN = "en"
    IT = "it"


class QuestionType(str, enum.Enum):
    """Survey question types."""

    FREE_TEXT = "free_text"
    NUMERIC = "numeric"
    SCALE = "scale"


class ContactState(str, enum.Enum):
    """Contact lifecycle state."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REFUSED = "refused"
    NOT_REACHED = "not_reached"
    EXCLUDED = "excluded"


class ContactOutcome(str, enum.Enum):
    """Call attempt outcome."""

    COMPLETED = "completed"
    REFUSED = "refused"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"


class UserRole(str, enum.Enum):
    """User roles."""

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"


class User(Base):
    """User entity."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    oidc_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_type=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Campaign(Base):
    """Campaign entity."""

    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status", create_type=False),
        nullable=False,
    )
    language: Mapped[CampaignLanguage] = mapped_column(
        Enum(CampaignLanguage, name="campaign_language", create_type=False),
        nullable=False,
    )
    intro_script: Mapped[str] = mapped_column(Text, nullable=False)
    question_1_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_1_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", create_type=False),
        nullable=False,
    )
    question_2_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_2_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", create_type=False),
        nullable=False,
    )
    question_3_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_3_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", create_type=False),
        nullable=False,
    )
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_call_start_local: Mapped[time] = mapped_column(Time, nullable=False)
    allowed_call_end_local: Mapped[time] = mapped_column(Time, nullable=False)
    email_completed_template_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("email_templates.id"), nullable=True
    )
    email_refused_template_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("email_templates.id"), nullable=True
    )
    email_not_reached_template_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("email_templates.id"), nullable=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="campaign", lazy="selectin"
    )
    call_attempts: Mapped[list["CallAttempt"]] = relationship(
        "CallAttempt", back_populates="campaign", lazy="selectin"
    )


class Contact(Base):
    """Contact entity."""

    __tablename__ = "contacts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    campaign_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    external_contact_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, default="auto")
    has_prior_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    do_not_call: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[ContactState] = mapped_column(
        Enum(ContactState, name="contact_state", create_type=False),
        nullable=False,
    )
    attempts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_outcome: Mapped[Optional[ContactOutcome]] = mapped_column(
        Enum(ContactOutcome, name="contact_outcome", create_type=False),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="contacts")


class CallAttempt(Base):
    """Call attempt entity."""

    __tablename__ = "call_attempts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    call_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    provider_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    answered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[Optional[ContactOutcome]] = mapped_column(
        Enum(ContactOutcome, name="contact_outcome", create_type=False),
        nullable=True,
    )
    provider_raw_status: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="call_attempts")


class SurveyResponse(Base):
    """Survey response entity."""

    __tablename__ = "survey_responses"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False
    )
    call_attempt_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("call_attempts.id"), nullable=False
    )
    q1_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    q2_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    q3_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    q1_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    q2_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    q3_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)