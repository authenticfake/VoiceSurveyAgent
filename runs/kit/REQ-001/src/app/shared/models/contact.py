"""Contact model definition."""
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base
from app.shared.models.enums import ContactState, ContactLanguage, CallOutcome

class Contact(Base):
    """Contact entity representing a survey target."""
    
    __tablename__ = "contacts"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_contact_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_language: Mapped[ContactLanguage] = mapped_column(
        SAEnum(ContactLanguage, name="contact_language", create_type=False),
        nullable=False,
        default=ContactLanguage.AUTO,
    )
    has_prior_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    do_not_call: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    state: Mapped[ContactState] = mapped_column(
        SAEnum(ContactState, name="contact_state", create_type=False),
        nullable=False,
        default=ContactState.PENDING,
        index=True,
    )
    attempts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_outcome: Mapped[CallOutcome | None] = mapped_column(
        SAEnum(CallOutcome, name="call_outcome", create_type=False),
        nullable=True,
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
    campaign = relationship("Campaign", foreign_keys=[campaign_id])