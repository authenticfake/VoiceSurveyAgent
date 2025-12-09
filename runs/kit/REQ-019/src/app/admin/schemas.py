"""
Admin configuration schemas.

REQ-019: Admin configuration API
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProviderType(str, Enum):
    """Telephony provider type."""

    TELEPHONY_API = "telephony_api"
    VOICE_AI_PLATFORM = "voice_ai_platform"


class LLMProvider(str, Enum):
    """LLM provider type."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure-openai"
    GOOGLE = "google"


class TelephonyConfigResponse(BaseModel):
    """Telephony configuration response."""

    provider_type: ProviderType
    provider_name: str
    outbound_number: str
    max_concurrent_calls: int
    # Credentials are never returned in responses

    class Config:
        from_attributes = True


class LLMConfigResponse(BaseModel):
    """LLM configuration response."""

    llm_provider: LLMProvider
    llm_model: str
    # API keys are never returned in responses

    class Config:
        from_attributes = True


class EmailConfigResponse(BaseModel):
    """Email configuration response."""

    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    # Password/API keys are never returned

    class Config:
        from_attributes = True


class RetentionConfigResponse(BaseModel):
    """Retention configuration response."""

    recording_retention_days: int
    transcript_retention_days: int

    class Config:
        from_attributes = True


class AdminConfigResponse(BaseModel):
    """Complete admin configuration response."""

    id: UUID
    telephony: TelephonyConfigResponse
    llm: LLMConfigResponse
    email: EmailConfigResponse
    retention: RetentionConfigResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TelephonyConfigUpdate(BaseModel):
    """Telephony configuration update request."""

    provider_type: Optional[ProviderType] = None
    provider_name: Optional[str] = Field(None, min_length=1, max_length=100)
    outbound_number: Optional[str] = Field(None, min_length=1, max_length=20)
    max_concurrent_calls: Optional[int] = Field(None, ge=1, le=100)
    api_key: Optional[str] = Field(None, min_length=1, description="Stored in Secrets Manager")
    api_secret: Optional[str] = Field(None, min_length=1, description="Stored in Secrets Manager")
    account_sid: Optional[str] = Field(None, min_length=1, description="Stored in Secrets Manager")


class LLMConfigUpdate(BaseModel):
    """LLM configuration update request."""

    llm_provider: Optional[LLMProvider] = None
    llm_model: Optional[str] = Field(None, min_length=1, max_length=100)
    api_key: Optional[str] = Field(None, min_length=1, description="Stored in Secrets Manager")


class EmailConfigUpdate(BaseModel):
    """Email configuration update request."""

    smtp_host: Optional[str] = Field(None, min_length=1, max_length=255)
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_username: Optional[str] = Field(None, max_length=255)
    smtp_password: Optional[str] = Field(None, min_length=1, description="Stored in Secrets Manager")
    from_email: Optional[str] = Field(None, max_length=255)
    from_name: Optional[str] = Field(None, max_length=255)

    @field_validator("from_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class RetentionConfigUpdate(BaseModel):
    """Retention configuration update request."""

    recording_retention_days: Optional[int] = Field(None, ge=1, le=3650)
    transcript_retention_days: Optional[int] = Field(None, ge=1, le=3650)


class AdminConfigUpdate(BaseModel):
    """Complete admin configuration update request."""

    telephony: Optional[TelephonyConfigUpdate] = None
    llm: Optional[LLMConfigUpdate] = None
    email: Optional[EmailConfigUpdate] = None
    retention: Optional[RetentionConfigUpdate] = None


class AuditLogEntry(BaseModel):
    """Audit log entry for configuration changes."""

    id: UUID
    user_id: UUID
    user_email: str
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    changes: dict
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log response."""

    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
    total_pages: int