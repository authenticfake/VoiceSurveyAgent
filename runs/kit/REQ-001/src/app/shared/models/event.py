"""Event model definition."""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base
from app.shared.models.enums import EventType


class Event(Base):
    """Event entity for survey lifecycle events."""
    
    __tablename__ = "events"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, name="event_type", create_type=False),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_attempts.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    campaign = relationship("Campaign", backref="events")
    contact = relationship("Contact", backref="events")
    call_attempt = relationship("CallAttempt", backref="events")