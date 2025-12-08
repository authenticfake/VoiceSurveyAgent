import json

import boto3
from botocore.stub import Stubber

from app.infra.messaging import (
    MessageEnvelope,
    SqsMessageConsumer,
    SqsMessagePublisher,
)


def test_sqs_publisher_fifo_params():
    client = boto3.client("sqs", region_name="eu-central-1")
    stubber = Stubber(client)
    queue_url = "https://sqs.eu-central-1.amazonaws.com/123/survey-events.fifo"
    envelope = MessageEnvelope(
        id="event-1",
        body={"event_type": "survey.completed", "payload": {"contact_id": "c-1"}},
        group_id="survey-events",
    )

    stubber.add_response(
        "send_message",
        {"MessageId": "abc-123"},
        {
            "QueueUrl": queue_url,
            "MessageBody": json.dumps(envelope.body),
            "MessageGroupId": "survey-events",
            "MessageDeduplicationId": "event-1",
        },
    )

    publisher = SqsMessagePublisher(client, queue_url, fifo=True, default_group_id="survey-events")

    with stubber:
        message_id = publisher.publish(envelope)

    assert message_id == "abc-123"


def test_sqs_consumer_receive_and_delete():
    client = boto3.client("sqs", region_name="eu-central-1")
    stubber = Stubber(client)
    queue_url = "https://sqs.eu-central-1.amazonaws.com/123/survey-events"

    body = {"event_type": "survey.refused", "payload": {"contact_id": "c-2"}}
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
            "VisibilityTimeout": 30,
            "WaitTimeSeconds": 10,
            "MessageAttributeNames": ["All"],
        },
    )
    stubber.add_response(
        "delete_message",
        {},
        {"QueueUrl": queue_url, "ReceiptHandle": "rh-1"},
    )

    consumer = SqsMessageConsumer(
        client=client,
        queue_url=queue_url,
        visibility_timeout=30,
        wait_time_seconds=10,
        max_number_of_messages=5,
    )

    with stubber:
        messages = consumer.receive()
        assert len(messages) == 1
        consumer.delete(messages[0].receipt_handle)