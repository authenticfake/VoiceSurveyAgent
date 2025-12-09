"""
Event schemas for survey events.

REQ-015: Event publisher service
- Event schema includes event_type, campaign_id, contact_id, call_id
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Survey event types."""

    SURVEY_COMPLETED = "survey.completed"
    SURVEY_REFUSED = "survey.refused"
    SURVEY_NOT_REACHED = "survey.not_reached"


class SurveyEvent(BaseModel):
    """Base survey event schema."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    campaign_id: str
    contact_id: str
    call_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attempts_count: int = 1

    class Config:
        use_enum_values = True


class SurveyCompletedEvent(SurveyEvent):
    """Event published when a survey is completed successfully."""

    event_type: EventType = EventType.SURVEY_COMPLETED
    answers: list[str] = Field(default_factory=list)
    q1_answer: Optional[str] = None
    q2_answer: Optional[str] = None
    q3_answer: Optional[str] = None
    q1_confidence: Optional[float] = None
    q2_confidence: Optional[float] = None
    q3_confidence: Optional[float] = None


class SurveyRefusedEvent(SurveyEvent):
    """Event published when a survey is refused by the contact."""

    event_type: EventType = EventType.SURVEY_REFUSED
    refusal_reason: Optional[str] = None


class SurveyNotReachedEvent(SurveyEvent):
    """Event published when a contact could not be reached after max attempts."""

    event_type: EventType = EventType.SURVEY_NOT_REACHED
    total_attempts: int = 0
    last_outcome: Optional[str] = None