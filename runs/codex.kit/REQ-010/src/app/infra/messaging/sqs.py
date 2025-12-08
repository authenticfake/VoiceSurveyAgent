from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Sequence

import boto3
from botocore.client import BaseClient
from botocore.config import Config as BotoCoreConfig

_logger = logging.getLogger("app.infra.messaging.sqs")


def _json_default(obj: Any) -> str:
    """Fallback JSON serializer."""
    return str(obj)


@dataclass(frozen=True)
class MessageEnvelope:
    """High-level event envelope pushed to SQS."""

    id: str
    body: Dict[str, Any]
    deduplication_id: str | None = None
    group_id: str | None = None
    attributes: Dict[str, Any] | None = field(default=None)


@dataclass(frozen=True)
class ReceivedMessage:
    """Structured representation of an SQS message."""

    message_id: str
    receipt_handle: str
    body: str
    attributes: Dict[str, Any]


class SqsMessagePublisher:
    """Thin wrapper around boto3 send_message with FIFO awareness."""

    def __init__(
        self,
        client: BaseClient,
        queue_url: str,
        fifo: bool = False,
        default_group_id: str | None = None,
    ) -> None:
        self._client = client
        self._queue_url = queue_url
        self._fifo = fifo
        self._default_group_id = default_group_id

    def publish(self, envelope: MessageEnvelope) -> str:
        """Publish the envelope and return the provider message id."""
        msg_attributes = {}
        if envelope.attributes:
            for key, value in envelope.attributes.items():
                msg_attributes[key] = {
                    "DataType": "String",
                    "StringValue": str(value),
                }

        params: Dict[str, Any] = {
            "QueueUrl": self._queue_url,
            "MessageBody": json.dumps(envelope.body, default=_json_default),
        }
        if msg_attributes:
            params["MessageAttributes"] = msg_attributes

        if self._fifo:
            group_id = envelope.group_id or self._default_group_id
            if not group_id:
                raise ValueError(
                    "FIFO queues require a message group id; none was provided."
                )
            params["MessageGroupId"] = group_id
            params["MessageDeduplicationId"] = (
                envelope.deduplication_id or envelope.id
            )

        response = self._client.send_message(**params)
        message_id = response["MessageId"]
        _logger.debug(
            "sqs_message_published",
            extra={
                "queue_url": self._queue_url,
                "message_id": message_id,
                "deduplication_id": envelope.deduplication_id or envelope.id,
            },
        )
        return message_id


class SqsMessageConsumer:
    """Polling helper with delete semantics."""

    def __init__(
        self,
        client: BaseClient,
        queue_url: str,
        *,
        visibility_timeout: int,
        wait_time_seconds: int,
        max_number_of_messages: int,
    ) -> None:
        self._client = client
        self._queue_url = queue_url
        self._visibility_timeout = visibility_timeout
        self._wait_time_seconds = wait_time_seconds
        self._max_number_of_messages = max_number_of_messages

    def receive(self) -> List[ReceivedMessage]:
        """Receive up to max_number_of_messages messages via long polling."""
        params = {
            "QueueUrl": self._queue_url,
            "MaxNumberOfMessages": self._max_number_of_messages,
            "VisibilityTimeout": self._visibility_timeout,
            "WaitTimeSeconds": self._wait_time_seconds,
            "MessageAttributeNames": ["All"],
        }
        response = self._client.receive_message(**params)
        messages = response.get("Messages", [])
        received: List[ReceivedMessage] = []
        for message in messages:
            received.append(
                ReceivedMessage(
                    message_id=message["MessageId"],
                    receipt_handle=message["ReceiptHandle"],
                    body=message["Body"],
                    attributes=message.get("MessageAttributes", {}),
                )
            )
        if received:
            _logger.debug(
                "sqs_messages_received",
                extra={"count": len(received), "queue_url": self._queue_url},
            )
        return received

    def delete(self, receipt_handle: str) -> None:
        """Delete a processed message via its receipt handle."""
        self._client.delete_message(
            QueueUrl=self._queue_url, ReceiptHandle=receipt_handle
        )
        _logger.debug(
            "sqs_message_deleted",
            extra={"queue_url": self._queue_url, "receipt_handle": receipt_handle},
        )


def build_sqs_client(
    queue_region: str,
    *,
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
    session_token: str | None = None,
    boto_config_factory: Callable[[], BotoCoreConfig] | None = None,
) -> BaseClient:
    """Create a boto3 SQS client based on provided credentials."""
    session = boto3.session.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token,
        region_name=queue_region,
    )
    config = boto_config_factory() if boto_config_factory else BotoCoreConfig()
    return session.client("sqs", config=config)