"""Exclusion list entry model definition."""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base
from app.shared.models.enums import ExclusionSource

class ExclusionListEntry(Base):
    """Exclusion list entry for do-not-call numbers."""
    
    __tablename__ = "exclusion_list_entries"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[ExclusionSource] = mapped_column(
        SAEnum(ExclusionSource, name="exclusion_source", create_type=False),
        nullable=False,
        default=ExclusionSource.MANUAL,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )