from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SurveyEventType(str, Enum):
    """Allowed survey event types."""

    COMPLETED = "survey.completed"
    REFUSED = "survey.refused"
    NOT_REACHED = "survey.not_reached"


class SurveyAnswerModel(BaseModel):
    """Structured answer captured by the dialogue stack."""

    question_number: int = Field(..., ge=1, le=3)
    answer_text: str = Field(..., min_length=1, max_length=4000)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SurveyEventMessage(BaseModel):
    """Canonical message schema published to the event bus."""

    event_id: UUID
    event_type: SurveyEventType
    campaign_id: UUID
    contact_id: UUID
    call_attempt_id: Optional[UUID] = None
    call_id: Optional[str] = None
    timestamp: datetime
    attempts_count: int = Field(..., ge=0)
    answers: List[SurveyAnswerModel] = Field(default_factory=list)
    outcome: str = Field(..., min_length=1)
    email: Optional[str] = None
    locale: Optional[str] = None
    payload_version: str = Field(default="1.0", frozen=True)

    def deduplication_key(self) -> str:
        """Stable key used for FIFO queues and idempotency."""
        call_component = self.call_attempt_id or self.call_id or "na"
        return f"{self.event_type}:{self.contact_id}:{call_component}"

    def message_group_id(self) -> str:
        """Group identifier for FIFO ordering (campaign scoped)."""
        return str(self.campaign_id)

    def to_message_attributes(self) -> Dict[str, Dict[str, str]]:
        """SQS-compatible message attributes to support filtering."""
        return {
            "event_type": {"DataType": "String", "StringValue": self.event_type.value},
            "campaign_id": {"DataType": "String", "StringValue": str(self.campaign_id)},
            "contact_id": {"DataType": "String", "StringValue": str(self.contact_id)},
            "payload_version": {"DataType": "String", "StringValue": self.payload_version},
        }


class EventPublishError(RuntimeError):
    """Raised when an event cannot be published to the external bus."""