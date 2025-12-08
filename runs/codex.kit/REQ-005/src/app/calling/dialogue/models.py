from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, PositiveInt, field_validator

from .enums import ConsentDecision, TelephonyEventName


class SurveyAnswerPayload(BaseModel):
    question_number: PositiveInt = Field(..., le=3)
    answer_text: str = Field(..., min_length=1, max_length=4000)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class DialoguePayload(BaseModel):
    consent_status: ConsentDecision
    consent_timestamp: datetime
    answers: List[SurveyAnswerPayload] = Field(default_factory=list)

    @field_validator("answers")
    @classmethod
    def ensure_unique_question(cls, answers: List[SurveyAnswerPayload]) -> List[SurveyAnswerPayload]:
        seen = {ans.question_number for ans in answers}
        if len(seen) != len(answers):
            raise ValueError("Answers must contain unique question numbers.")
        return answers


class TelephonyEventPayload(BaseModel):
    event: TelephonyEventName
    campaign_id: UUID
    contact_id: UUID
    call_id: str | None = None
    provider_call_id: str | None = None
    occurred_at: datetime
    error_code: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    dialogue: Optional[DialoguePayload] = None