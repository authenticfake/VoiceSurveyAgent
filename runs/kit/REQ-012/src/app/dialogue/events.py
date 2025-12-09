"""
Event publishing for dialogue orchestration.

REQ-012: Dialogue orchestrator consent flow
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol
from uuid import UUID, uuid4

class DialogueEventType(str, Enum):
    """Types of dialogue events."""

    SURVEY_COMPLETED = "survey.completed"
    SURVEY_REFUSED = "survey.refused"
    SURVEY_NOT_REACHED = "survey.not_reached"

@dataclass
class DialogueEvent:
    """Event data for dialogue events."""

    id: UUID = field(default_factory=uuid4)
    event_type: DialogueEventType = DialogueEventType.SURVEY_REFUSED
    campaign_id: str = ""
    contact_id: str = ""
    call_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Dictionary representation of the event.
        """
        return {
            "id": str(self.id),
            "event_type": self.event_type.value,
            "campaign_id": self.campaign_id,
            "contact_id": self.contact_id,
            "call_id": self.call_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }

class EventBusProtocol(Protocol):
    """Protocol for event bus integration."""

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """Publish message to event bus.

        Args:
            topic: Topic/queue name.
            message: Message payload.
        """
        ...

class DialogueEventPublisher:
    """Publisher for dialogue-related events."""

    TOPIC = "survey.events"

    def __init__(self, event_bus: EventBusProtocol) -> None:
        """Initialize event publisher.

        Args:
            event_bus: Event bus for publishing.
        """
        self._bus = event_bus

    async def publish_refused(
        self,
        campaign_id: str,
        contact_id: str,
        call_id: str,
        attempt_count: int,
    ) -> DialogueEvent:
        """Publish survey.refused event.

        Args:
            campaign_id: Campaign identifier.
            contact_id: Contact identifier.
            call_id: Call identifier.
            attempt_count: Number of attempts.

        Returns:
            Published event.
        """
        event = DialogueEvent(
            event_type=DialogueEventType.SURVEY_REFUSED,
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_id=call_id,
            payload={
                "attempts": attempt_count,
                "reason": "explicit_refusal",
            },
        )

        await self._bus.publish(self.TOPIC, event.to_dict())
        return event

    async def publish_completed(
        self,
        campaign_id: str,
        contact_id: str,
        call_id: str,
        answers: list[str],
        attempt_count: int,
    ) -> DialogueEvent:
        """Publish survey.completed event.

        Args:
            campaign_id: Campaign identifier.
            contact_id: Contact identifier.
            call_id: Call identifier.
            answers: List of survey answers.
            attempt_count: Number of attempts.

        Returns:
            Published event.
        """
        event = DialogueEvent(
            event_type=DialogueEventType.SURVEY_COMPLETED,
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_id=call_id,
            payload={
                "answers": answers,
                "attempts": attempt_count,
            },
        )

        await self._bus.publish(self.TOPIC, event.to_dict())
        return event

    async def publish_not_reached(
        self,
        campaign_id: str,
        contact_id: str,
        call_id: str,
        attempt_count: int,
    ) -> DialogueEvent:
        """Publish survey.not_reached event.

        Args:
            campaign_id: Campaign identifier.
            contact_id: Contact identifier.
            call_id: Call identifier.
            attempt_count: Total attempts made.

        Returns:
            Published event.
        """
        event = DialogueEvent(
            event_type=DialogueEventType.SURVEY_NOT_REACHED,
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_id=call_id,
            payload={
                "attempts": attempt_count,
                "reason": "max_attempts_reached",
            },
        )

        await self._bus.publish(self.TOPIC, event.to_dict())
        return event