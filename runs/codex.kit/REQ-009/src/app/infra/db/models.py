"""SQLAlchemy ORM models aligned with the SPEC data model."""
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


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"


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


class EventType(str, enum.Enum):
    COMPLETED = "survey.completed"
    REFUSED = "survey.refused"
    NOT_REACHED = "survey.not_reached"


class EmailTemplateType(str, enum.Enum):
    COMPLETED = "completed"
    REFUSED = "refused"
    NOT_REACHED = "not_reached"


class EmailNotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ProviderType(str, enum.Enum):
    TELEPHONY_API = "telephony_api"
    VOICE_AI_PLATFORM = "voice_ai_platform"


class LLMProvider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure-openai"
    GOOGLE = "google"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    oidc_sub: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(sa.String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, name="user_role_enum"), nullable=False
    )

    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign", back_populates="creator", cascade="all,delete-orphan"
    )


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
    locale: Mapped[CampaignLanguage] = mapped_column(
        sa.Enum(CampaignLanguage, name="campaign_language_enum"), nullable=False
    )
    subject: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(sa.Text, nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(sa.Text)

    notifications: Mapped[List["EmailNotification"]] = relationship(
        "EmailNotification", back_populates="template"
    )


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        sa.Index("ix_campaigns_status", "status"),
        sa.Index("ix_campaigns_language", "language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text)
    status: Mapped[CampaignStatus] = mapped_column(
        sa.Enum(CampaignStatus, name="campaign_status_enum"),
        nullable=False,
        default=CampaignStatus.DRAFT,
    )
    language: Mapped[CampaignLanguage] = mapped_column(
        sa.Enum(CampaignLanguage, name="campaign_language_enum"),
        nullable=False,
        default=CampaignLanguage.EN,
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
        UUID(as_uuid=True),
        sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
    )
    email_refused_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
    )
    email_not_reached_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
    )

    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    creator: Mapped[Optional[User]] = relationship("User", back_populates="campaigns")
    contacts: Mapped[List["Contact"]] = relationship(
        "Contact", back_populates="campaign", cascade="all,delete-orphan"
    )
    call_attempts: Mapped[List["CallAttempt"]] = relationship(
        "CallAttempt", back_populates="campaign"
    )


class ExclusionListEntry(TimestampMixin, Base):
    __tablename__ = "exclusion_list_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone_number: Mapped[str] = mapped_column(sa.String(32), nullable=False, unique=True)
    reason: Mapped[Optional[str]] = mapped_column(sa.String(255))
    source: Mapped[str] = mapped_column(sa.String(64), nullable=False)


class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        sa.UniqueConstraint(
            "campaign_id", "external_contact_id", name="uq_contacts_campaign_external"
        ),
        sa.UniqueConstraint(
            "campaign_id", "phone_number", name="uq_contacts_campaign_phone"
        ),
        sa.Index("ix_contacts_campaign_state", "campaign_id", "state"),
        sa.Index("ix_contacts_phone_number", "phone_number"),
        sa.CheckConstraint("attempts_count >= 0", name="ck_contacts_attempts_non_negative"),
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
        nullable=False,
        default=ContactLanguage.AUTO,
    )
    has_prior_consent: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    do_not_call: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    state: Mapped[ContactState] = mapped_column(
        sa.Enum(ContactState, name="contact_state_enum"),
        nullable=False,
        default=ContactState.PENDING,
    )
    attempts_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True))
    last_outcome: Mapped[Optional[CallOutcome]] = mapped_column(
        sa.Enum(CallOutcome, name="call_outcome_enum")
    )

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="contacts")
    call_attempts: Mapped[List["CallAttempt"]] = relationship(
        "CallAttempt", back_populates="contact", cascade="all,delete-orphan"
    )
    survey_response: Mapped[Optional["SurveyResponse"]] = relationship(
        "SurveyResponse", back_populates="contact", uselist=False
    )


class CallAttempt(TimestampMixin, Base):
    __tablename__ = "call_attempts"
    __table_args__ = (
        sa.UniqueConstraint("call_id", name="uq_call_attempts_call_id"),
        sa.UniqueConstraint("provider_call_id", name="uq_call_attempts_provider_call_id"),
        sa.Index("ix_call_attempts_contact_id", "contact_id"),
        sa.Index("ix_call_attempts_campaign_id", "campaign_id"),
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
    call_id: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    provider_call_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    answered_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True))
    outcome: Mapped[Optional[CallOutcome]] = mapped_column(
        sa.Enum(CallOutcome, name="call_outcome_enum")
    )
    provider_raw_status: Mapped[Optional[str]] = mapped_column(sa.String(255))
    error_code: Mapped[Optional[str]] = mapped_column(sa.String(64))
    metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
    )

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="call_attempts")
    contact: Mapped[Contact] = relationship("Contact", back_populates="call_attempts")
    survey_response: Mapped[Optional["SurveyResponse"]] = relationship(
        "SurveyResponse", back_populates="call_attempt", uselist=False
    )
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="call_attempt", cascade="all,delete-orphan"
    )
    transcript_snippets: Mapped[List["TranscriptSnippet"]] = relationship(
        "TranscriptSnippet", back_populates="call_attempt", cascade="all,delete-orphan"
    )


class SurveyResponse(TimestampMixin, Base):
    __tablename__ = "survey_responses"
    __table_args__ = (
        sa.UniqueConstraint("contact_id", name="uq_survey_responses_contact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    call_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("call_attempts.id", ondelete="CASCADE"), nullable=False
    )
    q1_answer: Mapped[str] = mapped_column(sa.Text, nullable=False)
    q2_answer: Mapped[str] = mapped_column(sa.Text, nullable=False)
    q3_answer: Mapped[str] = mapped_column(sa.Text, nullable=False)
    q1_confidence: Mapped[Optional[float]] = mapped_column(sa.Numeric(3, 2))
    q2_confidence: Mapped[Optional[float]] = mapped_column(sa.Numeric(3, 2))
    q3_confidence: Mapped[Optional[float]] = mapped_column(sa.Numeric(3, 2))
    completed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )

    contact: Mapped[Contact] = relationship("Contact", back_populates="survey_response")
    campaign: Mapped[Campaign] = relationship("Campaign")
    call_attempt: Mapped[CallAttempt] = relationship(
        "CallAttempt", back_populates="survey_response"
    )


class Event(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        sa.Index("ix_events_campaign_event", "campaign_id", "event_type"),
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
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
    )

    call_attempt: Mapped[Optional[CallAttempt]] = relationship(
        "CallAttempt", back_populates="events"
    )


class EmailNotification(TimestampMixin, Base):
    __tablename__ = "email_notifications"
    __table_args__ = (
        sa.Index("ix_email_notifications_status", "status"),
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
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("email_templates.id", ondelete="SET NULL")
    )
    to_email: Mapped[str] = mapped_column(sa.String(320), nullable=False)
    status: Mapped[EmailNotificationStatus] = mapped_column(
        sa.Enum(EmailNotificationStatus, name="email_notification_status_enum"),
        nullable=False,
        default=EmailNotificationStatus.PENDING,
    )
    provider_message_id: Mapped[Optional[str]] = mapped_column(sa.String(128))
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text)

    template: Mapped[Optional[EmailTemplate]] = relationship(
        "EmailTemplate", back_populates="notifications"
    )


class ProviderConfiguration(TimestampMixin, Base):
    __tablename__ = "provider_configurations"
    __table_args__ = (
        sa.UniqueConstraint("provider_type", name="uq_provider_configurations_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_type: Mapped[ProviderType] = mapped_column(
        sa.Enum(ProviderType, name="provider_type_enum"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    outbound_number: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    max_concurrent_calls: Mapped[int] = mapped_column(
        sa.SmallInteger, nullable=False
    )
    llm_provider: Mapped[LLMProvider] = mapped_column(
        sa.Enum(LLMProvider, name="llm_provider_enum"), nullable=False
    )
    llm_model: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    recording_retention_days: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    transcript_retention_days: Mapped[int] = mapped_column(sa.Integer, nullable=False)


class TranscriptSnippet(TimestampMixin, Base):
    __tablename__ = "transcript_snippets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    call_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("call_attempts.id", ondelete="CASCADE"), nullable=False
    )
    transcript_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    language: Mapped[CampaignLanguage] = mapped_column(
        sa.Enum(CampaignLanguage, name="campaign_language_enum"), nullable=False
    )

    call_attempt: Mapped[CallAttempt] = relationship(
        "CallAttempt", back_populates="transcript_snippets"
    )


__all__ = [
    "Base",
    "User",
    "EmailTemplate",
    "Campaign",
    "Contact",
    "ExclusionListEntry",
    "CallAttempt",
    "SurveyResponse",
    "Event",
    "EmailNotification",
    "ProviderConfiguration",
    "TranscriptSnippet",
    "UserRole",
    "CampaignStatus",
    "CampaignLanguage",
    "QuestionType",
    "ContactState",
    "ContactLanguage",
    "CallOutcome",
    "EventType",
    "EmailTemplateType",
    "EmailNotificationStatus",
    "ProviderType",
    "LLMProvider",
]