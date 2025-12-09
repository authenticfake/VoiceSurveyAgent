"""
Event service for publishing survey events.

REQ-015: Event publisher service
- Provides high-level API for publishing survey events
- Integrates with dialogue persistence layer
"""

from __future__ import annotations

import logging
from typing import Optional, Protocol
from uuid import UUID

from app.events.publisher import EventPublisher, SQSEventPublisher, EventPublisherConfig
from app.events.schemas import (
    SurveyCompletedEvent,
    SurveyRefusedEvent,
    SurveyNotReachedEvent,
    EventType,
)

logger = logging.getLogger(__name__)


class EventService:
    """
    Service for publishing survey events.

    Provides high-level methods for publishing different event types
    with proper data transformation and error handling.
    """

    def __init__(self, publisher: EventPublisher) -> None:
        """
        Initialize event service.

        Args:
            publisher: Event publisher implementation.
        """
        self._publisher = publisher

    def publish_survey_completed(
        self,
        campaign_id: str,
        contact_id: str,
        call_id: str,
        answers: list[str],
        attempts_count: int = 1,
        q1_confidence: Optional[float] = None,
        q2_confidence: Optional[float] = None,
        q3_confidence: Optional[float] = None,
    ) -> bool:
        """
        Publish a survey completed event.

        Args:
            campaign_id: Campaign UUID.
            contact_id: Contact UUID.
            call_id: Call attempt UUID.
            answers: List of 3 answers.
            attempts_count: Number of call attempts.
            q1_confidence: Confidence score for Q1.
            q2_confidence: Confidence score for Q2.
            q3_confidence: Confidence score for Q3.

        Returns:
            True if published successfully.
        """
        event = SurveyCompletedEvent(
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_id=call_id,
            answers=answers,
            attempts_count=attempts_count,
            q1_answer=answers[0] if len(answers) > 0 else None,
            q2_answer=answers[1] if len(answers) > 1 else None,
            q3_answer=answers[2] if len(answers) > 2 else None,
            q1_confidence=q1_confidence,
            q2_confidence=q2_confidence,
            q3_confidence=q3_confidence,
        )

        logger.info(
            "Publishing survey completed event",
            extra={
                "event_id": event.event_id,
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "call_id": call_id,
            },
        )

        return self._publisher.publish(event)

    def publish_survey_refused(
        self,
        campaign_id: str,
        contact_id: str,
        call_id: Optional[str] = None,
        attempts_count: int = 1,
        refusal_reason: Optional[str] = None,
    ) -> bool:
        """
        Publish a survey refused event.

        Args:
            campaign_id: Campaign UUID.
            contact_id: Contact UUID.
            call_id: Call attempt UUID (optional).
            attempts_count: Number of call attempts.
            refusal_reason: Reason for refusal.

        Returns:
            True if published successfully.
        """
        event = SurveyRefusedEvent(
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_id=call_id,
            attempts_count=attempts_count,
            refusal_reason=refusal_reason,
        )

        logger.info(
            "Publishing survey refused event",
            extra={
                "event_id": event.event_id,
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "call_id": call_id,
            },
        )

        return self._publisher.publish(event)

    def publish_survey_not_reached(
        self,
        campaign_id: str,
        contact_id: str,
        total_attempts: int,
        last_outcome: Optional[str] = None,
        call_id: Optional[str] = None,
    ) -> bool:
        """
        Publish a survey not reached event.

        Args:
            campaign_id: Campaign UUID.
            contact_id: Contact UUID.
            total_attempts: Total number of call attempts.
            last_outcome: Last call outcome (no_answer, busy, failed).
            call_id: Last call attempt UUID (optional).

        Returns:
            True if published successfully.
        """
        event = SurveyNotReachedEvent(
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_id=call_id,
            total_attempts=total_attempts,
            attempts_count=total_attempts,
            last_outcome=last_outcome,
        )

        logger.info(
            "Publishing survey not reached event",
            extra={
                "event_id": event.event_id,
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "total_attempts": total_attempts,
            },
        )

        return self._publisher.publish(event)

    async def publish_survey_completed_async(
        self,
        campaign_id: str,
        contact_id: str,
        call_id: str,
        answers: list[str],
        attempts_count: int = 1,
        q1_confidence: Optional[float] = None,
        q2_confidence: Optional[float] = None,
        q3_confidence: Optional[float] = None,
    ) -> bool:
        """Async version of publish_survey_completed."""
        event = SurveyCompletedEvent(
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_id=call_id,
            answers=answers,
            attempts_count=attempts_count,
            q1_answer=answers[0] if len(answers) > 0 else None,
            q2_answer=answers[1] if len(answers) > 1 else None,
            q3_answer=answers[2] if len(answers) > 2 else None,
            q1_confidence=q1_confidence,
            q2_confidence=q2_confidence,
            q3_confidence=q3_confidence,
        )
        return await self._publisher.publish_async(event)

    async def publish_survey_refused_async(
        self,
        campaign_id: str,
        contact_id: str,
        call_id: Optional[str] = None,
        attempts_count: int = 1,
        refusal_reason: Optional[str] = None,
    ) -> bool:
        """Async version of publish_survey_refused."""
        event = SurveyRefusedEvent(
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_id=call_id,
            attempts_count=attempts_count,
            refusal_reason=refusal_reason,
        )
        return await self._publisher.publish_async(event)

    async def publish_survey_not_reached_async(
        self,
        campaign_id: str,
        contact_id: str,
        total_attempts: int,
        last_outcome: Optional[str] = None,
        call_id: Optional[str] = None,
    ) -> bool:
        """Async version of publish_survey_not_reached."""
        event = SurveyNotReachedEvent(
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_id=call_id,
            total_attempts=total_attempts,
            attempts_count=total_attempts,
            last_outcome=last_outcome,
        )
        return await self._publisher.publish_async(event)


def create_event_service(
    queue_url: str,
    region_name: str = "eu-central-1",
    max_retries: int = 3,
) -> EventService:
    """
    Factory function to create an EventService with SQS publisher.

    Args:
        queue_url: SQS queue URL.
        region_name: AWS region.
        max_retries: Maximum retry attempts.

    Returns:
        Configured EventService instance.
    """
    config = EventPublisherConfig(
        queue_url=queue_url,
        region_name=region_name,
        max_retries=max_retries,
    )
    publisher = SQSEventPublisher(config)
    return EventService(publisher)