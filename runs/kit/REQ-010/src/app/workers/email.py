from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Protocol

from app.infra.config import AppSettings, get_app_settings
from app.infra.messaging import (
    MessageEnvelope,
    ReceivedMessage,
    SqsMessageConsumer,
    build_sqs_client,
)
from app.infra.observability import configure_logging, get_logger
from app.workers.base import load_factory

logger = get_logger("app.workers.email")


@dataclass(frozen=True)
class SurveyEvent:
    """Structured representation of survey lifecycle events."""

    event_type: str
    payload: dict[str, Any]
    raw_message_id: str

    @staticmethod
    def from_received(message: ReceivedMessage) -> "SurveyEvent":
        body = json.loads(message.body)
        return SurveyEvent(
            event_type=body["event_type"],
            payload=body["payload"],
            raw_message_id=message.message_id,
        )


class EmailEventHandler(Protocol):
    """Handler contract for survey events."""

    def handle(self, event: SurveyEvent) -> None:  # pragma: no cover - protocol
        ...


class EmailWorker:
    """Consumes survey events and invokes the handler."""

    def __init__(self, consumer: SqsMessageConsumer, handler: EmailEventHandler) -> None:
        self._consumer = consumer
        self._handler = handler

    def run(self, max_loops: int | None = None) -> None:
        loops = 0
        while max_loops is None or loops < max_loops:
            loops += 1
            messages = self._consumer.receive()
            if not messages:
                continue
            for message in messages:
                try:
                    event = SurveyEvent.from_received(message)
                    self._handler.handle(event)
                    self._consumer.delete(message.receipt_handle)
                except Exception:  # pragma: no cover - defensive logging
                    logger.exception(
                        "email_worker_handle_failure",
                        extra={
                            "extra_fields": {
                                "message_id": message.message_id,
                                "event_body": message.body,
                            }
                        },
                    )
                    raise


def _build_handler(settings: AppSettings) -> EmailEventHandler:
    factory = load_factory(settings.email_worker.handler_factory_path)
    handler = factory(settings)
    if not hasattr(handler, "handle"):
        raise TypeError("Email handler factory must return an object with handle().")
    return handler


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="email-worker", description="Survey email notification worker"
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=None,
        help="Number of polling loops to execute (default: infinite).",
    )
    args = parser.parse_args(argv)

    settings = get_app_settings()
    configure_logging(
        service_name=settings.observability.service_name,
        level=settings.observability.log_level,
    )

    handler = _build_handler(settings)
    client = build_sqs_client(
        settings.messaging.region_name,
        access_key_id=settings.messaging.access_key_id,
        secret_access_key=settings.messaging.secret_access_key,
        session_token=settings.messaging.session_token,
    )
    consumer = SqsMessageConsumer(
        client=client,
        queue_url=settings.messaging.queue_url,
        visibility_timeout=settings.email_worker.visibility_timeout_seconds,
        wait_time_seconds=settings.email_worker.long_poll_seconds,
        max_number_of_messages=settings.email_worker.max_number_of_messages,
    )
    worker = EmailWorker(consumer=consumer, handler=handler)
    logger.info(
        "email_worker_started",
        extra={"extra_fields": {"environment": settings.environment}},
    )
    worker.run(max_loops=args.max_loops)
    logger.info("email_worker_stopped")


if __name__ == "__main__":
    main()