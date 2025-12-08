import json
from threading import Event

import boto3
from botocore.stub import Stubber

from app.infra.config import reset_settings_cache
from app.workers import scheduler
from app.workers.email import EmailWorker, SurveyEvent
from app.workers.scheduler import main as scheduler_main


def prepare_env(monkeypatch):
    monkeypatch.setenv("APP__DATABASE__URL", "postgresql://localhost/test")
    monkeypatch.setenv(
        "APP__MESSAGING__QUEUE_URL",
        "https://sqs.eu-central-1.amazonaws.com/123/survey-events",
    )
    monkeypatch.setenv("APP__MESSAGING__REGION_NAME", "eu-central-1")
    monkeypatch.setenv(
        "APP__SCHEDULER__FACTORY_PATH",
        "test.fixtures.dummy_scheduler_impl:build_scheduler",
    )
    monkeypatch.setenv(
        "APP__EMAIL_WORKER__HANDLER_FACTORY_PATH",
        "test.fixtures.dummy_email_handler:build_handler",
    )
    reset_settings_cache()


def test_scheduler_main_runs_single_cycle(monkeypatch):
    prepare_env(monkeypatch)
    monkeypatch.setenv("APP__PROVIDER__OUTBOUND_NUMBER", "+15005550006")
    monkeypatch.setenv("APP__PROVIDER__MAX_CONCURRENT_CALLS", "5")

    scheduler_main(["--once"])
    # fixture increments counter; import lazily to avoid cycle
    from test.fixtures.dummy_scheduler_impl import INVOCATIONS

    assert INVOCATIONS["count"] == 1


def test_email_worker_processes_message(monkeypatch):
    prepare_env(monkeypatch)
    client = boto3.client("sqs", region_name="eu-central-1")
    stubber = Stubber(client)
    queue_url = "https://sqs.eu-central-1.amazonaws.com/123/survey-events"
    body = {"event_type": "survey.completed", "payload": {"contact_id": "abc"}}

    stubber.add_response(
        "receive_message",
        {
            "Messages": [
                {
                    "MessageId": "mid-1",
                    "ReceiptHandle": "rh-1",
                    "Body": json.dumps(body),
                    "MessageAttributes": {},
                }
            ]
        },
        {
            "QueueUrl": queue_url,
            "MaxNumberOfMessages": 5,
            "VisibilityTimeout": 60,
            "WaitTimeSeconds": 20,
            "MessageAttributeNames": ["All"],
        },
    )
    stubber.add_response(
        "delete_message",
        {},
        {"QueueUrl": queue_url, "ReceiptHandle": "rh-1"},
    )

    from app.infra.messaging import SqsMessageConsumer

    consumer = SqsMessageConsumer(
        client=client,
        queue_url=queue_url,
        visibility_timeout=60,
        wait_time_seconds=20,
        max_number_of_messages=5,
    )

    from test.fixtures.dummy_email_handler import build_handler, HANDLED_EVENTS

    handler = build_handler(None)
    worker = EmailWorker(consumer, handler)

    with stubber:
        worker.run(max_loops=1)

    assert len(HANDLED_EVENTS) == 1
    assert HANDLED_EVENTS[0].payload["contact_id"] == "abc"