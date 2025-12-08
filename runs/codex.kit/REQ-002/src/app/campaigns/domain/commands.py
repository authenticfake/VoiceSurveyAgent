from dataclasses import dataclass
from datetime import time
from typing import Optional, Sequence
from uuid import UUID

from app.campaigns.domain.enums import CampaignLanguage, QuestionAnswerType


@dataclass(frozen=True)
class CampaignQuestionInput:
    text: str
    answer_type: QuestionAnswerType
    position: int


@dataclass(frozen=True)
class RetryPolicyInput:
    max_attempts: int
    retry_interval_minutes: int


@dataclass(frozen=True)
class CallWindowInput:
    start_local: time
    end_local: time


@dataclass(frozen=True)
class CampaignCreateCommand:
    name: str
    description: Optional[str]
    language: CampaignLanguage
    intro_script: str
    questions: Sequence[CampaignQuestionInput]
    retry_policy: RetryPolicyInput
    call_window: CallWindowInput
    email_completed_template_id: Optional[UUID]
    email_refused_template_id: Optional[UUID]
    email_not_reached_template_id: Optional[UUID]


@dataclass(frozen=True)
class CampaignUpdateCommand:
    name: Optional[str] = None
    description: Optional[str] = None
    language: Optional[CampaignLanguage] = None
    intro_script: Optional[str] = None
    questions: Optional[Sequence[CampaignQuestionInput]] = None
    retry_policy: Optional[RetryPolicyInput] = None
    call_window: Optional[CallWindowInput] = None
    email_completed_template_id: Optional[UUID] = None
    email_refused_template_id: Optional[UUID] = None
    email_not_reached_template_id: Optional[UUID] = None