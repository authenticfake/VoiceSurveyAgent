"""
SQLAlchemy models for contacts.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import Base

if TYPE_CHECKING:
    from app.campaigns.models import Campaign


class ContactState(str, Enum):
    """Contact lifecycle state."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REFUSED = "refused"
    NOT_REACHED = "not_reached"
    EXCLUDED = "excluded"


class ContactLanguage(str, Enum):
    """Contact preferred language."""

    EN = "en"
    IT = "it"
    AUTO = "auto"


class ContactOutcome(str, Enum):
    """Contact last call outcome."""

    COMPLETED = "completed"
    REFUSED = "refused"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"


class Contact(Base):
    """Contact model matching the database schema from REQ-001."""

    __tablename__ = "contacts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_contact_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    phone_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    preferred_language: Mapped[ContactLanguage] = mapped_column(
        SQLEnum(ContactLanguage, name="contact_language", create_type=False),
        nullable=False,
        default=ContactLanguage.AUTO,
    )
    has_prior_consent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    do_not_call: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    state: Mapped[ContactState] = mapped_column(
        SQLEnum(ContactState, name="contact_state", create_type=False),
        nullable=False,
        default=ContactState.PENDING,
    )
    attempts_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_outcome: Mapped[ContactOutcome | None] = mapped_column(
        SQLEnum(ContactOutcome, name="contact_outcome", create_type=False),
        nullable=True,
    )
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

    # Relationships
    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="contacts",
    )

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, phone={self.phone_number}, state={self.state})>"