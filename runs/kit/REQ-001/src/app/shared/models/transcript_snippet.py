"""Transcript snippet model definition."""
import uuid
from datetime import datetime

from sqlalchemy import Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base
from app.shared.models.enums import LanguageCode


class TranscriptSnippet(Base):
    """Transcript snippet entity for call transcripts."""
    
    __tablename__ = "transcript_snippets"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    call_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[LanguageCode] = mapped_column(
        SAEnum(LanguageCode, name="language_code", create_type=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    # Relationships
    call_attempt = relationship("CallAttempt", backref="transcript_snippets")