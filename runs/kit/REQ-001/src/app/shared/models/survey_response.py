"""Survey response model definition."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Text, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


class SurveyResponse(Base):
    """Survey response entity storing completed survey answers."""
    
    __tablename__ = "survey_responses"
    __table_args__ = (
        UniqueConstraint("contact_id", "campaign_id", name="uq_survey_responses_contact_campaign"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    q1_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    q2_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    q3_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    q1_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    q2_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    q3_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    # Relationships
    contact = relationship("Contact", backref="survey_responses")
    campaign = relationship("Campaign", backref="survey_responses")
    call_attempt = relationship("CallAttempt", backref="survey_response")