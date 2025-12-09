"""
Admin configuration database models.

REQ-019: Admin configuration API
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.shared.database import Base


class ProviderTypeEnum(str, enum.Enum):
    """Telephony provider type enum."""

    TELEPHONY_API = "telephony_api"
    VOICE_AI_PLATFORM = "voice_ai_platform"


class LLMProviderEnum(str, enum.Enum):
    """LLM provider enum."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure-openai"
    GOOGLE = "google"


class ProviderConfig(Base):
    """Provider configuration model - maps to provider_configs table."""

    __tablename__ = "provider_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_type = Column(
        Enum(ProviderTypeEnum, name="provider_type_enum", create_type=False),
        nullable=False,
        default=ProviderTypeEnum.TELEPHONY_API,
    )
    provider_name = Column(String(100), nullable=False, default="twilio")
    outbound_number = Column(String(20), nullable=False, default="+10000000000")
    max_concurrent_calls = Column(Integer, nullable=False, default=10)
    llm_provider = Column(
        Enum(LLMProviderEnum, name="llm_provider_enum", create_type=False),
        nullable=False,
        default=LLMProviderEnum.OPENAI,
    )
    llm_model = Column(String(100), nullable=False, default="gpt-4.1-mini")
    recording_retention_days = Column(Integer, nullable=False, default=180)
    transcript_retention_days = Column(Integer, nullable=False, default=180)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class EmailConfig(Base):
    """Email configuration model - separate table for email settings."""

    __tablename__ = "email_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_config_id = Column(UUID(as_uuid=True), ForeignKey("provider_configs.id"), nullable=False)
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    from_email = Column(String(255), nullable=True)
    from_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    provider_config = relationship("ProviderConfig", backref="email_config")


class AuditLog(Base):
    """Audit log model for tracking configuration changes."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # e.g., "config.update", "config.read"
    resource_type = Column(String(50), nullable=False)  # e.g., "provider_config", "email_config"
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    changes = Column(JSONB, nullable=False, default=dict)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="audit_logs")