from __future__ import annotations

import logging
from typing import Any, Dict

from botocore.client import BaseClient
from botocore.exceptions import ClientError

from .models import EventPublishError, SurveyEventMessage

logger = logging.getLogger(__name__)


class EventPublisher:
    """SQS-backed publisher for survey lifecycle events."""

    def __init__(self, queue_url: str, client: BaseClient):
        self._queue_url = queue_url
        self._client = client
        self._is_fifo = queue_url.endswith(".fifo")

    def publish(self, event: SurveyEventMessage) -> str:
        """Serialize and push the event to SQS."""
        body = event.model_dump_json()
        params: Dict[str, Any] = {
            "QueueUrl": self._queue_url,
            "MessageBody": body,
            "MessageAttributes": event.to_message_attributes(),
        }
        if self._is_fifo:
            params["MessageGroupId"] = event.message_group_id()
            params["MessageDeduplicationId"] = event.deduplication_key()

        try:
            response = self._client.send_message(**params)
        except ClientError as exc:  # pragma: no cover - network failure guard
            logger.exception("Failed to publish survey event %s", event.event_id)
            raise EventPublishError(str(exc)) from exc

        message_id = response.get("MessageId")
        if not message_id:
            raise EventPublishError("SQS send_message returned no MessageId")
        logger.debug("Published survey event %s as %s", event.event_id, message_id)
        return message_id