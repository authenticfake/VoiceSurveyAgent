"""
Event publishing module.

REQ-015: Event publisher service
- EventPublisher interface defines publish method
- SQS adapter implements publish to configured queue
- Event schema includes event_type, campaign_id, contact_id, call_id
- Message deduplication via call_id
- Failed publishes retried with exponential backoff
"""

from app.events.publisher import EventPublisher, SQSEventPublisher
from app.events.schemas import (
    SurveyEvent,
    SurveyCompletedEvent,
    SurveyRefusedEvent,
    SurveyNotReachedEvent,
    EventType,
)

__all__ = [
    "EventPublisher",
    "SQSEventPublisher",
    "SurveyEvent",
    "SurveyCompletedEvent",
    "SurveyRefusedEvent",
    "SurveyNotReachedEvent",
    "EventType",
]