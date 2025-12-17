"""
SQLAlchemy models for call attempts.

REQ-008: Call scheduler service
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import Base

if TYPE_CHECKING:
    from app.campaigns.models import Campaign
    from app.contacts.models import Contact


class CallOutcome(str, Enum):
    """Outcome of a call attempt."""

    COMPLETED = "completed"
    REFUSED = "refused"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"


class CallAttempt(Base):
    """Call attempt model matching the database schema from REQ-001."""

    __tablename__ = "call_attempts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    call_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    provider_call_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    outcome: Mapped[CallOutcome | None] = mapped_column(
        SQLEnum(CallOutcome, name="call_outcome", create_type=False),
        nullable=True,
    )
    provider_raw_status: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    # metadata: Mapped[dict[str, Any] | None] = mapped_column(
    #     JSONB,
    #     nullable=True,
    # )
    payload: Mapped[dict] = mapped_column("metadata", JSON, nullable=True, default=dict)


    # Relationships
    contact: Mapped["Contact"] = relationship(
        "Contact",
        back_populates="call_attempts",
        lazy="selectin",
    )
    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="call_attempts",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CallAttempt(id={self.id}, call_id={self.call_id}, outcome={self.outcome})>"