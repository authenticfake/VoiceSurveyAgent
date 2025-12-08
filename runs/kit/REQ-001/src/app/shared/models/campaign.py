"""Campaign model definition."""
import uuid
from datetime import datetime, time

from sqlalchemy import String, Text, Integer, Time, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType


class Campaign(Base):
    """Campaign entity representing a survey campaign."""
    
    __tablename__ = "campaigns"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        SAEnum(CampaignStatus, name="campaign_status", create_type=False),
        nullable=False,
        default=CampaignStatus.DRAFT,
    )
    language: Mapped[LanguageCode] = mapped_column(
        SAEnum(LanguageCode, name="language_code", create_type=False),
        nullable=False,
        default=LanguageCode.EN,
    )
    intro_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    question_1_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_1_type: Mapped[QuestionType | None] = mapped_column(
        SAEnum(QuestionType, name="question_type", create_type=False),
        nullable=True,
    )
    question_2_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_2_type: Mapped[QuestionType | None] = mapped_column(
        SAEnum(QuestionType, name="question_type", create_type=False),
        nullable=True,
    )
    question_3_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_3_type: Mapped[QuestionType | None] = mapped_column(
        SAEnum(QuestionType, name="question_type", create_type=False),
        nullable=True,
    )
    
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    allowed_call_start_local: Mapped[time | None] = mapped_column(Time, nullable=True)
    allowed_call_end_local: Mapped[time | None] = mapped_column(Time, nullable=True)
    
    email_completed_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_refused_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_not_reached_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    email_completed_template = relationship("EmailTemplate", foreign_keys=[email_completed_template_id])
    email_refused_template = relationship("EmailTemplate", foreign_keys=[email_refused_template_id])
    email_not_reached_template = relationship("EmailTemplate", foreign_keys=[email_not_reached_template_id])