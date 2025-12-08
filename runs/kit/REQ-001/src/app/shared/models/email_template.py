"""Email template model definition."""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base
from app.shared.models.enums import EmailTemplateType, LanguageCode


class EmailTemplate(Base):
    """Email template entity for notification emails."""
    
    __tablename__ = "email_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[EmailTemplateType] = mapped_column(
        SAEnum(EmailTemplateType, name="email_template_type", create_type=False),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[LanguageCode] = mapped_column(
        SAEnum(LanguageCode, name="language_code", create_type=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )