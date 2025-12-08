"""Provider configuration model definition."""
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base
from app.shared.models.enums import ProviderType, LLMProvider


class ProviderConfig(Base):
    """Provider configuration entity for telephony and LLM settings."""
    
    __tablename__ = "provider_config"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    provider_type: Mapped[ProviderType] = mapped_column(
        SAEnum(ProviderType, name="provider_type", create_type=False),
        nullable=False,
    )
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    outbound_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    max_concurrent_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    llm_provider: Mapped[LLMProvider] = mapped_column(
        SAEnum(LLMProvider, name="llm_provider", create_type=False),
        nullable=False,
    )
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    recording_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    transcript_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )