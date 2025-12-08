from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import boto3
from botocore.stub import Stubber

from app.events.bus.models import SurveyAnswerModel, SurveyEventMessage, SurveyEventType
from app.events.bus.publisher import EventPublisher


def test_event_publisher_sends_fifo_message():
    client = boto3.client("sqs", region_name="us-east-1")
    publisher = EventPublisher(
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/survey-events.fifo",
        client=client,
    )

    message = SurveyEventMessage(
        event_id=uuid4(),
        event_type=SurveyEventType.COMPLETED,
        campaign_id=uuid4(),
        contact_id=uuid4(),
        call_attempt_id=uuid4(),
        call_id="call-123",
        timestamp=datetime.now(timezone.utc),
        attempts_count=2,
        answers=[SurveyAnswerModel(question_number=1, answer_text="Yes", confidence=0.91)],
        outcome="completed",
        email="person@example.com",
        locale="en",
    )

    expected_params = {
        "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123456789012/survey-events.fifo",
        "MessageBody": message.model_dump_json(),
        "MessageGroupId": str(message.campaign_id),
        "MessageDeduplicationId": message.deduplication_key(),
        "MessageAttributes": message.to_message_attributes(),
    }

    with Stubber(client) as stubber:
        stubber.add_response(
            "send_message",
            {"MessageId": "abc123"},
            expected_params,
        )
        message_id = publisher.publish(message)

    assert message_id == "abc123"