from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignLanguage(str, enum.Enum):
    EN = "en"
    IT = "it"


class QuestionType(str, enum.Enum):
    FREE_TEXT = "free_text"
    NUMERIC = "numeric"
    SCALE = "scale"


class ContactState(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REFUSED = "refused"
    NOT_REACHED = "not_reached"
    EXCLUDED = "excluded"


class ContactLanguage(str, enum.Enum):
    AUTO = "auto"
    EN = "en"
    IT = "it"


class CallOutcome(str, enum.Enum):
    COMPLETED = "completed"
    REFUSED = "refused"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"


class EmailTemplateType(str, enum.Enum):
    COMPLETED = "completed"
    REFUSED = "refused"
    NOT_REACHED = "not_reached"


class EmailNotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class EventType(str, enum.Enum):
    SURVEY_COMPLETED = "survey.completed"
    SURVEY_REFUSED = "survey.refused"
    SURVEY_NOT_REACHED = "survey.not_reached"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    oidc_sub: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(sa.String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role: Mapped[str] = mapped_column(sa.String(64), nullable=False)


class EmailTemplate(TimestampMixin, Base):
    __tablename__ = "email_templates"
    __table_args__ = (
        sa.UniqueConstraint("type", "locale", name="uq_email_templates_type_locale"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    type: Mapped[EmailTemplateType] = mapped_column(
        sa.Enum(EmailTemplateType, name="email_template_type_enum"), nullable=False
    )
    locale: Mapped[str] = mapped_column(sa.String(8), nullable=False)
    subject: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(sa.Text, nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(sa.Text)

    notifications: Mapped[List["EmailNotification"]] = relationship(
        "EmailNotification", back_populates="template"
    )


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text)
    status: Mapped[CampaignStatus] = mapped_column(
        sa.Enum(CampaignStatus, name="campaign_status_enum"),
        default=CampaignStatus.DRAFT,
        nullable=False,
    )
    language: Mapped[CampaignLanguage] = mapped_column(
        sa.Enum(CampaignLanguage, name="campaign_language_enum"),
        default=CampaignLanguage.EN,
        nullable=False,
    )
    intro_script: Mapped[str] = mapped_column(sa.Text, nullable=False)
    question_1_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    question_1_type: Mapped[QuestionType] = mapped_column(
        sa.Enum(QuestionType, name="question_type_enum"), nullable=False
    )
    question_2_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    question_2_type: Mapped[QuestionType] = mapped_column(
        sa.Enum(QuestionType, name="question_type_enum"), nullable=False
    )
    question_3_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    question_3_type: Mapped[QuestionType] = mapped_column(
        sa.Enum(QuestionType, name="question_type_enum"), nullable=False
    )
    max_attempts: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    retry_interval_minutes: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    allowed_call_start_local: Mapped[datetime] = mapped_column(sa.Time, nullable=False)
    allowed_call_end_local: Mapped[datetime] = mapped_column(sa.Time, nullable=False)
    email_completed_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("email_templates.id", ondelete="SET NULL")
    )
    email_refused_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("email_templates.id", ondelete="SET NULL")
    )
    email_not_reached_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("email_templates.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    contacts: Mapped[List["Contact"]] = relationship(
        "Contact", back_populates="campaign", cascade="all,delete-orphan"
    )
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="campaign", cascade="all,delete-orphan"
    )


class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        sa.Index("ix_contacts_campaign_id", "campaign_id"),
        sa.Index("ix_contacts_phone_number", "phone_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    external_contact_id: Mapped[Optional[str]] = mapped_column(sa.String(255))
    phone_number: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(sa.String(320))
    preferred_language: Mapped[ContactLanguage] = mapped_column(
        sa.Enum(ContactLanguage, name="contact_language_enum"),
        default=ContactLanguage.AUTO,
        nullable=False,
    )
    has_prior_consent: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    do_not_call: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    state: Mapped[ContactState] = mapped_column(
        sa.Enum(ContactState, name="contact_state_enum"),
        default=ContactState.PENDING,
        nullable=False,
    )
    attempts_count: Mapped[int] = mapped_column(sa.SmallInteger, default=0, nullable=False)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True))
    last_outcome: Mapped[Optional[CallOutcome]] = mapped_column(
        sa.Enum(CallOutcome, name="call_outcome_enum")
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="contacts")
    call_attempts: Mapped[List["CallAttempt"]] = relationship(
        "CallAttempt", back_populates="contact", cascade="all,delete-orphan"
    )
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="contact", cascade="all,delete-orphan"
    )


class CallAttempt(TimestampMixin, Base):
    __tablename__ = "call_attempts"
    __table_args__ = (
        sa.UniqueConstraint("call_id", name="uq_call_attempts_call_id"),
        sa.Index("ix_call_attempts_contact_id", "contact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    call_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    provider_call_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    answered_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True))
    outcome: Mapped[Optional[CallOutcome]] = mapped_column(
        sa.Enum(CallOutcome, name="call_outcome_enum")
    )
    provider_raw_status: Mapped[Optional[str]] = mapped_column(sa.String(255))
    error_code: Mapped[Optional[str]] = mapped_column(sa.String(64))
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    campaign: Mapped["Campaign"] = relationship("Campaign")
    contact: Mapped["Contact"] = relationship("Contact", back_populates="call_attempts")
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="call_attempt", cascade="all,delete-orphan"
    )


class Event(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        sa.Index("ix_events_campaign_id", "campaign_id"),
        sa.Index("ix_events_contact_id", "contact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[EventType] = mapped_column(
        sa.Enum(EventType, name="event_type_enum"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    call_attempt_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("call_attempts.id", ondelete="SET NULL")
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="events")
    contact: Mapped["Contact"] = relationship("Contact", back_populates="events")
    call_attempt: Mapped[Optional["CallAttempt"]] = relationship(
        "CallAttempt", back_populates="events"
    )
    notifications: Mapped[List["EmailNotification"]] = relationship(
        "EmailNotification", back_populates="event", cascade="all,delete-orphan"
    )


class EmailNotification(TimestampMixin, Base):
    __tablename__ = "email_notifications"
    __table_args__ = (
        sa.Index("ix_email_notifications_status", "status"),
        sa.UniqueConstraint("event_id", name="uq_email_notifications_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("email_templates.id", ondelete="SET NULL")
    )
    to_email: Mapped[str] = mapped_column(sa.String(320), nullable=False)
    status: Mapped[EmailNotificationStatus] = mapped_column(
        sa.Enum(EmailNotificationStatus, name="email_notification_status_enum"),
        default=EmailNotificationStatus.PENDING,
        nullable=False,
    )
    provider_message_id: Mapped[Optional[str]] = mapped_column(sa.String(255))
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text)

    event: Mapped["Event"] = relationship("Event", back_populates="notifications")
    contact: Mapped["Contact"] = relationship("Contact")
    campaign: Mapped["Campaign"] = relationship("Campaign")
    template: Mapped[Optional["EmailTemplate"]] = relationship(
        "EmailTemplate", back_populates="notifications"
    )