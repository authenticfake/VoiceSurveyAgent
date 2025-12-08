from __future__ import annotations

from dataclasses import dataclass
from typing import List

import boto3
from botocore.client import BaseClient


@dataclass(frozen=True)
class SQSQueueConfig:
    queue_url: str
    region_name: str
    endpoint_url: str | None = None
    wait_time_seconds: int = 10
    max_number_of_messages: int = 5
    visibility_timeout: int | None = None


@dataclass(frozen=True)
class QueueMessage:
    message_id: str
    receipt_handle: str
    body: str
    attributes: dict[str, str]


class QueueConsumer:
    """Protocol-like base to enable typing without typing.Protocol dependency."""

    def receive_messages(self) -> List[QueueMessage]:  # pragma: no cover - interface
        raise NotImplementedError

    def delete_message(self, receipt_handle: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class SQSQueueConsumer(QueueConsumer):
    """Thin adapter around boto3's SQS client."""

    def __init__(self, client: BaseClient, config: SQSQueueConfig):
        self._client = client
        self._config = config

    def receive_messages(self) -> List[QueueMessage]:
        params = {
            "QueueUrl": self._config.queue_url,
            "MaxNumberOfMessages": self._config.max_number_of_messages,
            "WaitTimeSeconds": self._config.wait_time_seconds,
            "MessageAttributeNames": ["All"],
        }
        if self._config.visibility_timeout:
            params["VisibilityTimeout"] = self._config.visibility_timeout

        response = self._client.receive_message(**params)
        result: List[QueueMessage] = []
        for raw in response.get("Messages", []):
            result.append(
                QueueMessage(
                    message_id=raw["MessageId"],
                    receipt_handle=raw["ReceiptHandle"],
                    body=raw["Body"],
                    attributes=raw.get("Attributes", {}),
                )
            )
        return result

    def delete_message(self, receipt_handle: str) -> None:
        self._client.delete_message(
            QueueUrl=self._config.queue_url, ReceiptHandle=receipt_handle
        )


def build_sqs_client(config: SQSQueueConfig) -> BaseClient:
    """Factory separated for easier testing and configuration."""
    return boto3.client(
        "sqs", region_name=config.region_name, endpoint_url=config.endpoint_url
    )