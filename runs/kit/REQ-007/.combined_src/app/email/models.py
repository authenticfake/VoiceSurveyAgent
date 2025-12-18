from __future__ import annotations

import uuid

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.auth.models import Base


class EmailTemplate(Base):
    """Minimal template table required by Campaign FK columns."""
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=True)
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
