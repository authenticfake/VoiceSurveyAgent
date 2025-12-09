"""
Event publisher interface and SQS implementation.

REQ-015: Event publisher service
- EventPublisher interface defines publish method
- SQS adapter implements publish to configured queue
- Message deduplication via call_id
- Failed publishes retried with exponential backoff
"""

from __future__ import annotations

import json
import logging
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Optional, Protocol

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel

from app.events.schemas import SurveyEvent

logger = logging.getLogger(__name__)


class EventPublisherConfig(BaseModel):
    """Configuration for event publisher."""

    queue_url: str
    region_name: str = "eu-central-1"
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0


class EventPublisher(Protocol):
    """Interface for event publishing."""

    def publish(self, event: SurveyEvent) -> bool:
        """
        Publish an event to the event bus.

        Args:
            event: The survey event to publish.

        Returns:
            True if published successfully, False otherwise.
        """
        ...

    async def publish_async(self, event: SurveyEvent) -> bool:
        """
        Publish an event asynchronously.

        Args:
            event: The survey event to publish.

        Returns:
            True if published successfully, False otherwise.
        """
        ...


class SQSEventPublisher:
    """
    SQS implementation of EventPublisher.

    Implements:
    - Message deduplication via call_id
    - Exponential backoff retry on failures
    """

    def __init__(
        self,
        config: EventPublisherConfig,
        sqs_client: Optional[boto3.client] = None,
    ) -> None:
        """
        Initialize SQS event publisher.

        Args:
            config: Publisher configuration.
            sqs_client: Optional SQS client for dependency injection.
        """
        self._config = config
        self._client = sqs_client or boto3.client(
            "sqs",
            region_name=config.region_name,
        )

    def _generate_deduplication_id(self, event: SurveyEvent) -> str:
        """
        Generate deduplication ID from event.

        Uses call_id if available, otherwise generates from event_id.
        """
        if event.call_id:
            # Use call_id for deduplication as per acceptance criteria
            base = f"{event.event_type}:{event.call_id}"
        else:
            # Fallback to event_id
            base = f"{event.event_type}:{event.event_id}"

        return hashlib.sha256(base.encode()).hexdigest()[:128]

    def _generate_message_group_id(self, event: SurveyEvent) -> str:
        """Generate message group ID for FIFO queues."""
        return f"campaign-{event.campaign_id}"

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self._config.base_delay_seconds * (2 ** attempt)
        return min(delay, self._config.max_delay_seconds)

    def publish(self, event: SurveyEvent) -> bool:
        """
        Publish an event to SQS with retry logic.

        Args:
            event: The survey event to publish.

        Returns:
            True if published successfully, False otherwise.
        """
        message_body = event.model_dump_json()
        dedup_id = self._generate_deduplication_id(event)
        group_id = self._generate_message_group_id(event)

        for attempt in range(self._config.max_retries):
            try:
                # Check if queue is FIFO (ends with .fifo)
                is_fifo = self._config.queue_url.endswith(".fifo")

                send_params = {
                    "QueueUrl": self._config.queue_url,
                    "MessageBody": message_body,
                    "MessageAttributes": {
                        "event_type": {
                            "DataType": "String",
                            "StringValue": event.event_type,
                        },
                        "campaign_id": {
                            "DataType": "String",
                            "StringValue": event.campaign_id,
                        },
                        "contact_id": {
                            "DataType": "String",
                            "StringValue": event.contact_id,
                        },
                    },
                }

                if is_fifo:
                    send_params["MessageDeduplicationId"] = dedup_id
                    send_params["MessageGroupId"] = group_id

                if event.call_id:
                    send_params["MessageAttributes"]["call_id"] = {
                        "DataType": "String",
                        "StringValue": event.call_id,
                    }

                response = self._client.send_message(**send_params)

                logger.info(
                    "Event published successfully",
                    extra={
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "campaign_id": event.campaign_id,
                        "contact_id": event.contact_id,
                        "call_id": event.call_id,
                        "message_id": response.get("MessageId"),
                        "deduplication_id": dedup_id,
                    },
                )
                return True

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                logger.warning(
                    "Failed to publish event, retrying",
                    extra={
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "attempt": attempt + 1,
                        "max_retries": self._config.max_retries,
                        "error_code": error_code,
                        "error": str(e),
                    },
                )

                if attempt < self._config.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    time.sleep(delay)
                else:
                    logger.error(
                        "Failed to publish event after all retries",
                        extra={
                            "event_id": event.event_id,
                            "event_type": event.event_type,
                            "campaign_id": event.campaign_id,
                            "contact_id": event.contact_id,
                            "call_id": event.call_id,
                            "error": str(e),
                        },
                    )
                    return False

            except Exception as e:
                logger.error(
                    "Unexpected error publishing event",
                    extra={
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "error": str(e),
                    },
                )
                return False

        return False

    async def publish_async(self, event: SurveyEvent) -> bool:
        """
        Publish an event asynchronously.

        For now, delegates to synchronous publish.
        Can be enhanced with aioboto3 for true async.

        Args:
            event: The survey event to publish.

        Returns:
            True if published successfully, False otherwise.
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.publish, event)


class InMemoryEventPublisher:
    """
    In-memory event publisher for testing.

    Stores published events in a list for verification.
    """

    def __init__(self) -> None:
        """Initialize in-memory publisher."""
        self.events: list[SurveyEvent] = []
        self.publish_count: int = 0
        self.should_fail: bool = False
        self.fail_count: int = 0

    def publish(self, event: SurveyEvent) -> bool:
        """
        Publish an event to in-memory storage.

        Args:
            event: The survey event to publish.

        Returns:
            True if published successfully, False if configured to fail.
        """
        self.publish_count += 1

        if self.should_fail:
            self.fail_count += 1
            logger.warning(
                "InMemoryEventPublisher configured to fail",
                extra={"event_id": event.event_id},
            )
            return False

        self.events.append(event)
        logger.info(
            "Event published to in-memory store",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "total_events": len(self.events),
            },
        )
        return True

    async def publish_async(self, event: SurveyEvent) -> bool:
        """
        Publish an event asynchronously.

        Args:
            event: The survey event to publish.

        Returns:
            True if published successfully, False otherwise.
        """
        return self.publish(event)

    def clear(self) -> None:
        """Clear all stored events."""
        self.events.clear()
        self.publish_count = 0
        self.fail_count = 0

    def get_events_by_type(self, event_type: str) -> list[SurveyEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_campaign(self, campaign_id: str) -> list[SurveyEvent]:
        """Get all events for a specific campaign."""
        return [e for e in self.events if e.campaign_id == campaign_id]

    def get_events_by_contact(self, contact_id: str) -> list[SurveyEvent]:
        """Get all events for a specific contact."""
        return [e for e in self.events if e.contact_id == contact_id]