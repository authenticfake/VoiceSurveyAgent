from __future__ import annotations

import logging
import time
from typing import Optional

from pydantic import ValidationError

from app.events.bus.models import SurveyEventMessage
from app.infra.messaging.sqs import QueueConsumer

from .service import EmailNotificationProcessor

logger = logging.getLogger(__name__)


class SurveyEmailWorker:
    """Polls the survey event queue and triggers notification processing."""

    def __init__(
        self,
        queue_consumer: QueueConsumer,
        processor: EmailNotificationProcessor,
        idle_sleep_seconds: float = 5.0,
    ):
        self._queue_consumer = queue_consumer
        self._processor = processor
        self._idle_sleep_seconds = idle_sleep_seconds

    def run_once(self) -> int:
        processed = 0
        for message in self._queue_consumer.receive_messages():
            try:
                payload = SurveyEventMessage.model_validate_json(message.body)
            except ValidationError:
                logger.exception("Discarding malformed event payload: %s", message.body)
                self._queue_consumer.delete_message(message.receipt_handle)
                continue

            try:
                result = self._processor.process(payload)
                logger.debug(
                    "Processed event %s with outcome %s", payload.event_id, result.status
                )
                processed += 1
                self._queue_consumer.delete_message(message.receipt_handle)
            except Exception:  # pragma: no cover - safety net keeps retries via visibility timeout
                logger.exception("Failed to process event %s", payload.event_id)
        return processed

    def run_forever(self) -> None:  # pragma: no cover - blocking loop
        while True:
            processed = self.run_once()
            if processed == 0:
                time.sleep(self._idle_sleep_seconds)