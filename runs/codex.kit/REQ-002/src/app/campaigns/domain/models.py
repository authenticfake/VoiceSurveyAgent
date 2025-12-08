from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional
from uuid import UUID

from app.campaigns.domain.enums import (
    CampaignLanguage,
    CampaignStatus,
    QuestionAnswerType,
)


@dataclass(frozen=True)
class CampaignQuestion:
    position: int
    text: str
    answer_type: QuestionAnswerType


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    retry_interval_minutes: int


@dataclass(frozen=True)
class CallWindow:
    start_local: time
    end_local: time


@dataclass(frozen=True)
class EmailTemplateConfig:
    completed_template_id: Optional[UUID]
    refused_template_id: Optional[UUID]
    not_reached_template_id: Optional[UUID]


@dataclass(frozen=True)
class CampaignRecord:
    id: UUID
    name: str
    description: Optional[str]
    status: CampaignStatus
    language: CampaignLanguage
    intro_script: str
    questions: List[CampaignQuestion]
    retry_policy: RetryPolicy
    call_window: CallWindow
    email_templates: EmailTemplateConfig
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime