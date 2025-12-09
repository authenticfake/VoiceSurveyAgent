"""
SQLAlchemy ORM models for voicesurveyagent.

REQ-018: Campaign CSV export
"""

import enum
from datetime import datetime, time
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


# Enums
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
    EN = "en"
    IT = "it"
    AUTO = "auto"


class CallOutcome(str, enum.Enum):
    COMPLETED = "completed"
    REFUSED = "refused"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"


class EventType(str, enum.Enum):
    SURVEY_COMPLETED = "survey.completed"
    SURVEY_REFUSED = "survey.refused"
    SURVEY_NOT_REACHED = "survey.not_reached"


class EmailNotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class EmailTemplateType(str, enum.Enum):
    COMPLETED = "completed"
    REFUSED = "refused"
    NOT_REACHED = "not_reached"


class ProviderType(str, enum.Enum):
    TELEPHONY_API = "telephony_api"
    VOICE_AI_PLATFORM = "voice_ai_platform"


class LLMProvider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure-openai"
    GOOGLE = "google"


class ExclusionSource(str, enum.Enum):
    IMPORT = "import"
    API = "api"
    MANUAL = "manual"


class ExportJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Models
class User(Base):
    """User entity for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    oidc_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="created_by_user"
    )


class Campaign(Base):
    """Campaign entity for survey campaigns."""

    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"),
        nullable=False,
        default=CampaignStatus.DRAFT,
    )
    language: Mapped[CampaignLanguage] = mapped_column(
        Enum(CampaignLanguage, name="campaign_language"),
        nullable=False,
        default=CampaignLanguage.EN,
    )
    intro_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    question_1_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    question_1_type: Mapped[Optional[QuestionType]] = mapped_column(
        Enum(QuestionType, name="question_type"), nullable=True
    )
    question_2_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    question_2_type: Mapped[Optional[QuestionType]] = mapped_column(
        Enum(QuestionType, name="question_type"), nullable=True
    )
    question_3_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    question_3_type: Mapped[Optional[QuestionType]] = mapped_column(
        Enum(QuestionType, name="question_type"), nullable=True
    )

    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    allowed_call_start_local: Mapped[Optional[time]] = mapped_column(
        Time, nullable=True
    )
    allowed_call_end_local: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    email_completed_template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_refused_template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_not_reached_template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    created_by_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="campaigns"
    )
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="campaign"
    )
    call_attempts: Mapped[list["CallAttempt"]] = relationship(
        "CallAttempt", back_populates="campaign"
    )
    survey_responses: Mapped[list["SurveyResponse"]] = relationship(
        "SurveyResponse", back_populates="campaign"
    )
    events: Mapped[list["Event"]] = relationship("Event", back_populates="campaign")
    export_jobs: Mapped[list["ExportJob"]] = relationship(
        "ExportJob", back_populates="campaign"
    )


class Contact(Base):
    """Contact entity for survey contacts."""

    __tablename__ = "contacts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    campaign_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_contact_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    preferred_language: Mapped[ContactLanguage] = mapped_column(
        Enum(ContactLanguage, name="contact_language"),
        nullable=False,
        default=ContactLanguage.AUTO,
    )
    has_prior_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    do_not_call: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[ContactState] = mapped_column(
        Enum(ContactState, name="contact_state"),
        nullable=False,
        default=ContactState.PENDING,
    )
    attempts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_outcome: Mapped[Optional[CallOutcome]] = mapped_column(
        Enum(CallOutcome, name="call_outcome"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="contacts")
    call_attempts: Mapped[list["CallAttempt"]] = relationship(
        "CallAttempt", back_populates="contact"
    )
    survey_response: Mapped[Optional["SurveyResponse"]] = relationship(
        "SurveyResponse", back_populates="contact", uselist=False
    )

    __table_args__ = (
        Index("ix_contacts_campaign_state", "campaign_id", "state"),
    )


class ExclusionListEntry(Base):
    """Exclusion list entry for do-not-call numbers."""

    __tablename__ = "exclusion_list_entries"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    phone_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[ExclusionSource] = mapped_column(
        Enum(ExclusionSource, name="exclusion_source"),
        nullable=False,
        default=ExclusionSource.MANUAL,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class CallAttempt(Base):
    """Call attempt entity for tracking call attempts."""

    __tablename__ = "call_attempts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    contact_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    call_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    provider_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    answered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    outcome: Mapped[Optional[CallOutcome]] = mapped_column(
        Enum(CallOutcome, name="call_outcome"), nullable=True
    )
    provider_raw_status: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    contact: Mapped["Contact"] = relationship("Contact", back_populates="call_attempts")
    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="call_attempts"
    )
    survey_response: Mapped[Optional["SurveyResponse"]] = relationship(
        "SurveyResponse", back_populates="call_attempt", uselist=False
    )


class SurveyResponse(Base):
    """Survey response entity for storing survey answers."""

    __tablename__ = "survey_responses"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    contact_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_attempt_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    q1_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    q2_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    q3_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    q1_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    q2_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    q3_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    contact: Mapped["Contact"] = relationship(
        "Contact", back_populates="survey_response"
    )
    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="survey_responses"
    )
    call_attempt: Mapped["CallAttempt"] = relationship(
        "CallAttempt", back_populates="survey_response"
    )


class Event(Base):
    """Event entity for tracking survey events."""

    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type"), nullable=False
    )
    campaign_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    call_attempt_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_attempts.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="events")


class EmailTemplate(Base):
    """Email template entity for email notifications."""

    __tablename__ = "email_templates"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[EmailTemplateType] = mapped_column(
        Enum(EmailTemplateType, name="email_template_type"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locale: Mapped[CampaignLanguage] = mapped_column(
        Enum(CampaignLanguage, name="campaign_language"),
        nullable=False,
        default=CampaignLanguage.EN,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class EmailNotification(Base):
    """Email notification entity for tracking sent emails."""

    __tablename__ = "email_notifications"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    event_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[EmailNotificationStatus] = mapped_column(
        Enum(EmailNotificationStatus, name="email_notification_status"),
        nullable=False,
        default=EmailNotificationStatus.PENDING,
    )
    provider_message_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ProviderConfig(Base):
    """Provider configuration entity."""

    __tablename__ = "provider_configs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    provider_type: Mapped[ProviderType] = mapped_column(
        Enum(ProviderType, name="provider_type"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    outbound_number: Mapped[str] = mapped_column(String(50), nullable=False)
    max_concurrent_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    llm_provider: Mapped[LLMProvider] = mapped_column(
        Enum(LLMProvider, name="llm_provider"), nullable=False
    )
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    recording_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=180
    )
    transcript_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=180
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class TranscriptSnippet(Base):
    """Transcript snippet entity for storing call transcripts."""

    __tablename__ = "transcript_snippets"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    call_attempt_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[CampaignLanguage] = mapped_column(
        Enum(CampaignLanguage, name="campaign_language"),
        nullable=False,
        default=CampaignLanguage.EN,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class ExportJob(Base):
    """Export job entity for tracking CSV export jobs."""

    __tablename__ = "export_jobs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    campaign_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[ExportJobStatus] = mapped_column(
        Enum(ExportJobStatus, name="export_job_status"),
        nullable=False,
        default=ExportJobStatus.PENDING,
    )
    s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    download_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_records: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="export_jobs")