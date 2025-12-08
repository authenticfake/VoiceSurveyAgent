from __future__ import annotations

from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderType(str, Enum):
    TELEPHONY_API = "telephony_api"
    VOICE_AI_PLATFORM = "voice_ai_platform"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure-openai"
    GOOGLE = "google"


class EmailTemplateType(str, Enum):
    COMPLETED = "completed"
    REFUSED = "refused"
    NOT_REACHED = "not_reached"


class Locale(str, Enum):
    EN = "en"
    IT = "it"


class ProviderConfigModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_type: ProviderType
    provider_name: str
    outbound_number: str
    max_concurrent_calls: int = Field(..., ge=1)
    llm_provider: LLMProvider
    llm_model: str
    recording_retention_days: int = Field(..., ge=1)
    transcript_retention_days: int = Field(..., ge=1)


class ProviderConfigUpdateModel(BaseModel):
    provider_type: ProviderType
    provider_name: str = Field(..., min_length=1)
    outbound_number: str = Field(..., min_length=4)
    max_concurrent_calls: int = Field(..., ge=1, le=200)
    llm_provider: LLMProvider
    llm_model: str = Field(..., min_length=2)


class RetentionSettingsModel(BaseModel):
    recording_retention_days: int = Field(..., ge=1, le=3650)
    transcript_retention_days: int = Field(..., ge=1, le=3650)


class EmailProviderSettingsModel(BaseModel):
    provider: str = Field(..., min_length=2)
    from_email: Optional[str] = None
    reply_to_email: Optional[str] = None
    region: Optional[str] = None


class EmailTemplateModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: EmailTemplateType
    locale: Locale
    subject: str
    body_html: str
    body_text: Optional[str] = None


class EmailTemplateUpdateModel(BaseModel):
    id: UUID
    name: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None

    @field_validator("body_html", "body_text")
    @classmethod
    def non_empty_when_provided(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("Email template body cannot be blank.")
        return value


class AdminConfigurationView(BaseModel):
    provider: ProviderConfigModel
    retention: RetentionSettingsModel
    email_provider: EmailProviderSettingsModel
    email_templates: List[EmailTemplateModel] = Field(default_factory=list)


class AdminConfigurationUpdateRequest(BaseModel):
    provider: ProviderConfigUpdateModel
    retention: RetentionSettingsModel
    email_templates: List[EmailTemplateUpdateModel] = Field(default_factory=list)