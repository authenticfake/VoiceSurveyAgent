from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.infra.db.models import Event, EventType


@dataclass(frozen=True)
class SurveyEvent:
    event_type: EventType
    campaign_id: UUID
    contact_id: UUID
    call_attempt_id: UUID | None
    payload: Mapping[str, object]
    occurred_at: datetime


class SurveyEventPublisher(Protocol):
    def publish(self, event: SurveyEvent) -> None: ...


class DbSurveyEventPublisher(SurveyEventPublisher):
    """Persists survey events to the events table for downstream processing."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def publish(self, event: SurveyEvent) -> None:
        model = Event(
            event_type=event.event_type,
            campaign_id=event.campaign_id,
            contact_id=event.contact_id,
            call_attempt_id=event.call_attempt_id,
            payload=dict(event.payload),
            created_at=event.occurred_at,
        )
        self.session.add(model)