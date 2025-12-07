from __future__ import annotations

from datetime import datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, conlist

from app.campaigns.domain.commands import (
    CallWindowInput,
    CampaignCreateCommand,
    CampaignQuestionInput,
    CampaignUpdateCommand,
    RetryPolicyInput,
)
from app.campaigns.domain.enums import CampaignLanguage, CampaignStatus, QuestionAnswerType


class CampaignQuestionModel(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    answer_type: QuestionAnswerType


class RetryPolicyModel(BaseModel):
    max_attempts: int = Field(..., ge=1, le=5)
    retry_interval_minutes: int = Field(..., ge=1)


class CallWindowModel(BaseModel):
    start_local: time
    end_local: time


class EmailTemplatesModel(BaseModel):
    completed_template_id: Optional[UUID] = None
    refused_template_id: Optional[UUID] = None
    not_reached_template_id: Optional[UUID] = None


class CampaignBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    language: CampaignLanguage
    intro_script: str = Field(..., min_length=1)
    questions: conlist(CampaignQuestionModel, min_length=3, max_length=3)
    retry_policy: RetryPolicyModel
    allowed_call_window: CallWindowModel
    email_templates: EmailTemplatesModel | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    def _to_question_inputs(self) -> List[CampaignQuestionInput]:
        return [
            CampaignQuestionInput(
                text=question.text.strip(),
                answer_type=question.answer_type,
                position=index + 1,
            )
            for index, question in enumerate(self.questions)
        ]

    def _to_retry_policy_input(self) -> RetryPolicyInput:
        return RetryPolicyInput(
            max_attempts=self.retry_policy.max_attempts,
            retry_interval_minutes=self.retry_policy.retry_interval_minutes,
        )

    def _to_call_window_input(self) -> CallWindowInput:
        return CallWindowInput(
            start_local=self.allowed_call_window.start_local,
            end_local=self.allowed_call_window.end_local,
        )


class CampaignCreateRequest(CampaignBase):
    def to_command(self) -> CampaignCreateCommand:
        email_templates = self.email_templates or EmailTemplatesModel()
        return CampaignCreateCommand(
            name=self.name.strip(),
            description=self.description.strip() if self.description else None,
            language=self.language,
            intro_script=self.intro_script.strip(),
            questions=self._to_question_inputs(),
            retry_policy=self._to_retry_policy_input(),
            call_window=self._to_call_window_input(),
            email_completed_template_id=email_templates.completed_template_id,
            email_refused_template_id=email_templates.refused_template_id,
            email_not_reached_template_id=email_templates.not_reached_template_id,
        )


class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    language: Optional[CampaignLanguage] = None
    intro_script: Optional[str] = Field(default=None, min_length=1)
    questions: Optional[conlist(CampaignQuestionModel, min_length=3, max_length=3)] = None
    retry_policy: Optional[RetryPolicyModel] = None
    allowed_call_window: Optional[CallWindowModel] = None
    email_templates: Optional[EmailTemplatesModel] = None

    model_config = ConfigDict(str_strip_whitespace=True)

    def to_command(self) -> CampaignUpdateCommand:
        question_inputs = (
            [
                CampaignQuestionInput(
                    text=question.text.strip(),
                    answer_type=question.answer_type,
                    position=index + 1,
                )
                for index, question in enumerate(self.questions or [])
            ]
            if self.questions
            else None
        )

        return CampaignUpdateCommand(
            name=self.name.strip() if self.name else None,
            description=self.description.strip() if self.description else None,
            language=self.language,
            intro_script=self.intro_script.strip() if self.intro_script else None,
            questions=question_inputs,
            retry_policy=RetryPolicyInput(
                max_attempts=self.retry_policy.max_attempts,
                retry_interval_minutes=self.retry_policy.retry_interval_minutes,
            )
            if self.retry_policy
            else None,
            call_window=CallWindowInput(
                start_local=self.allowed_call_window.start_local,
                end_local=self.allowed_call_window.end_local,
            )
            if self.allowed_call_window
            else None,
            email_completed_template_id=(
                self.email_templates.completed_template_id if self.email_templates else None
            ),
            email_refused_template_id=(
                self.email_templates.refused_template_id if self.email_templates else None
            ),
            email_not_reached_template_id=(
                self.email_templates.not_reached_template_id if self.email_templates else None
            ),
        )


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    status: CampaignStatus
    language: CampaignLanguage
    intro_script: str
    questions: List[CampaignQuestionModel]
    retry_policy: RetryPolicyModel
    allowed_call_window: CallWindowModel
    email_templates: EmailTemplatesModel
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginationMetadata(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class CampaignListResponse(BaseModel):
    items: List[CampaignResponse]
    pagination: PaginationMetadata