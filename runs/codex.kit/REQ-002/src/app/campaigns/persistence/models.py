import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.campaigns.domain.enums import CampaignLanguage, CampaignStatus
from app.infra.db.base import Base


class CampaignModel(Base):
    __tablename__ = "campaigns"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(CampaignStatus, name="campaign_status_enum"),
        nullable=False,
        default=CampaignStatus.draft,
    )
    language = Column(
        Enum(CampaignLanguage, name="campaign_language_enum"),
        nullable=False,
        default=CampaignLanguage.en,
    )
    intro_script = Column(Text, nullable=False)

    question_1_text = Column(Text, nullable=False)
    question_1_type = Column(String(32), nullable=False)
    question_2_text = Column(Text, nullable=False)
    question_2_type = Column(String(32), nullable=False)
    question_3_text = Column(Text, nullable=False)
    question_3_type = Column(String(32), nullable=False)

    max_attempts = Column(Integer, nullable=False)
    retry_interval_minutes = Column(Integer, nullable=False)
    allowed_call_start_local = Column(Time, nullable=False)
    allowed_call_end_local = Column(Time, nullable=False)

    email_completed_template_id = Column(PGUUID(as_uuid=True), nullable=True)
    email_refused_template_id = Column(PGUUID(as_uuid=True), nullable=True)
    email_not_reached_template_id = Column(PGUUID(as_uuid=True), nullable=True)

    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (Index("ix_campaigns_status", "status"),)