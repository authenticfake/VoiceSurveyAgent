"""
SQS message consumer for email worker.

REQ-016: Email worker service
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Callable, Awaitable
from uuid import UUID

import aioboto3

from app.email.config import SQSConfig

logger = logging.getLogger(__name__)


@dataclass
class SQSMessage:
    """Parsed SQS message."""
    receipt_handle: str
    message_id: str
    body: dict
    attributes: dict


@dataclass
class SurveyEvent:
    """Parsed survey event from SQS."""
    event_type: str
    campaign_id: UUID
    contact_id: UUID
    call_id: Optional[str]
    timestamp: str
    outcome: Optional[str]
    answers: Optional[list[str]]
    attempts: Optional[int]
    raw_payload: dict


class SQSConsumer:
    """
    Consumes messages from SQS queue.
    
    Provides async iteration over messages with automatic
    visibility timeout management.
    """
    
    def __init__(self, config: SQSConfig):
        """
        Initialize SQS consumer.
        
        Args:
            config: SQS configuration.
        """
        self._config = config
        self._session = aioboto3.Session()
        self._running = False
    
    async def consume(self) -> AsyncIterator[tuple[SQSMessage, SurveyEvent]]:
        """
        Consume messages from queue.
        
        Yields:
            Tuple of (SQSMessage, SurveyEvent) for each message.
        """
        self._running = True
        
        async with self._session.client(
            "sqs",
            region_name=self._config.region,
        ) as sqs:
            while self._running:
                try:
                    response = await sqs.receive_message(
                        QueueUrl=self._config.queue_url,
                        MaxNumberOfMessages=self._config.max_messages,
                        WaitTimeSeconds=self._config.wait_time_seconds,
                        VisibilityTimeout=self._config.visibility_timeout,
                        AttributeNames=["All"],
                        MessageAttributeNames=["All"],
                    )
                    
                    messages = response.get("Messages", [])
                    
                    for msg in messages:
                        try:
                            sqs_message = self._parse_sqs_message(msg)
                            event = self._parse_survey_event(sqs_message.body)
                            yield sqs_message, event
                        except Exception as e:
                            logger.error(f"Failed to parse message {msg.get('MessageId')}: {e}")
                            # Delete malformed messages to prevent infinite retry
                            await self._delete_message(sqs, msg["ReceiptHandle"])
                    
                    if not messages:
                        # No messages, brief pause before next poll
                        await asyncio.sleep(1)
                        
                except asyncio.CancelledError:
                    logger.info("SQS consumer cancelled")
                    break
                except Exception as e:
                    logger.exception(f"Error consuming from SQS: {e}")
                    await asyncio.sleep(5)  # Back off on errors
    
    async def acknowledge(self, receipt_handle: str) -> None:
        """
        Acknowledge (delete) a processed message.
        
        Args:
            receipt_handle: SQS receipt handle.
        """
        async with self._session.client(
            "sqs",
            region_name=self._config.region,
        ) as sqs:
            await self._delete_message(sqs, receipt_handle)
    
    async def _delete_message(self, sqs, receipt_handle: str) -> None:
        """Delete message from queue."""
        try:
            await sqs.delete_message(
                QueueUrl=self._config.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
    
    def stop(self) -> None:
        """Stop consuming messages."""
        self._running = False
    
    def _parse_sqs_message(self, raw: dict) -> SQSMessage:
        """Parse raw SQS message."""
        body = json.loads(raw["Body"])
        return SQSMessage(
            receipt_handle=raw["ReceiptHandle"],
            message_id=raw["MessageId"],
            body=body,
            attributes=raw.get("Attributes", {}),
        )
    
    def _parse_survey_event(self, body: dict) -> SurveyEvent:
        """Parse survey event from message body."""
        return SurveyEvent(
            event_type=body["event_type"],
            campaign_id=UUID(body["campaign_id"]),
            contact_id=UUID(body["contact_id"]),
            call_id=body.get("call_id"),
            timestamp=body.get("timestamp", ""),
            outcome=body.get("outcome"),
            answers=body.get("answers"),
            attempts=body.get("attempts"),
            raw_payload=body,
        )