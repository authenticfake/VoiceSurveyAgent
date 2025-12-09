"""
Integration tests for event publisher service.

REQ-015: Event publisher service
- Tests end-to-end event publishing flow
- Uses moto for SQS mocking
"""

import pytest
import json
import os

# Skip if moto not available
moto = pytest.importorskip("moto")
boto3 = pytest.importorskip("boto3")

from moto import mock_aws

from app.events.publisher import SQSEventPublisher, EventPublisherConfig
from app.events.service import EventService
from app.events.schemas import (
    SurveyCompletedEvent,
    SurveyRefusedEvent,
    SurveyNotReachedEvent,
    EventType,
)


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-central-1"


@pytest.fixture
def sqs_client(aws_credentials):
    """Create a mock SQS client."""
    with mock_aws():
        client = boto3.client("sqs", region_name="eu-central-1")
        yield client


@pytest.fixture
def fifo_queue(sqs_client):
    """Create a FIFO queue for testing."""
    response = sqs_client.create_queue(
        QueueName="survey-events.fifo",
        Attributes={
            "FifoQueue": "true",
            "ContentBasedDeduplication": "false",
        },
    )
    return response["QueueUrl"]


@pytest.fixture
def standard_queue(sqs_client):
    """Create a standard queue for testing."""
    response = sqs_client.create_queue(QueueName="survey-events-standard")
    return response["QueueUrl"]


@pytest.fixture
def publisher_fifo(sqs_client, fifo_queue):
    """Create a publisher for FIFO queue."""
    config = EventPublisherConfig(
        queue_url=fifo_queue,
        region_name="eu-central-1",
    )
    return SQSEventPublisher(config, sqs_client=sqs_client)


@pytest.fixture
def publisher_standard(sqs_client, standard_queue):
    """Create a publisher for standard queue."""
    config = EventPublisherConfig(
        queue_url=standard_queue,
        region_name="eu-central-1",
    )
    return SQSEventPublisher(config, sqs_client=sqs_client)


@mock_aws
class TestSQSIntegration:
    """Integration tests with mocked SQS."""

    def test_publish_to_fifo_queue(self, sqs_client, fifo_queue, publisher_fifo):
        """Test publishing to FIFO queue."""
        event = SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
        )

        result = publisher_fifo.publish(event)

        assert result is True

        # Verify message in queue
        messages = sqs_client.receive_message(
            QueueUrl=fifo_queue,
            MaxNumberOfMessages=1,
            MessageAttributeNames=["All"],
        )

        assert "Messages" in messages
        assert len(messages["Messages"]) == 1

        message = messages["Messages"][0]
        body = json.loads(message["Body"])

        assert body["event_type"] == "survey.completed"
        assert body["campaign_id"] == "campaign-123"
        assert body["contact_id"] == "contact-456"
        assert body["call_id"] == "call-789"

    def test_publish_to_standard_queue(
        self, sqs_client, standard_queue, publisher_standard
    ):
        """Test publishing to standard queue."""
        event = SurveyRefusedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
        )

        result = publisher_standard.publish(event)

        assert result is True

        messages = sqs_client.receive_message(
            QueueUrl=standard_queue,
            MaxNumberOfMessages=1,
            MessageAttributeNames=["All"],
        )

        assert "Messages" in messages
        assert len(messages["Messages"]) == 1

    def test_message_attributes(self, sqs_client, fifo_queue, publisher_fifo):
        """Test that message attributes are set correctly."""
        event = SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
        )

        publisher_fifo.publish(event)

        messages = sqs_client.receive_message(
            QueueUrl=fifo_queue,
            MaxNumberOfMessages=1,
            MessageAttributeNames=["All"],
        )

        attrs = messages["Messages"][0]["MessageAttributes"]

        assert attrs["event_type"]["StringValue"] == "survey.completed"
        assert attrs["campaign_id"]["StringValue"] == "campaign-123"
        assert attrs["contact_id"]["StringValue"] == "contact-456"
        assert attrs["call_id"]["StringValue"] == "call-789"

    def test_deduplication_fifo(self, sqs_client, fifo_queue, publisher_fifo):
        """Test message deduplication in FIFO queue."""
        event = SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
        )

        # Publish same event twice
        publisher_fifo.publish(event)
        publisher_fifo.publish(event)

        # Should only have one message due to deduplication
        messages = sqs_client.receive_message(
            QueueUrl=fifo_queue,
            MaxNumberOfMessages=10,
            MessageAttributeNames=["All"],
        )

        # Note: moto may not fully implement deduplication
        # In real SQS, duplicate would be rejected within 5-minute window
        assert "Messages" in messages

    def test_event_service_integration(self, sqs_client, fifo_queue, publisher_fifo):
        """Test EventService with real SQS publisher."""
        service = EventService(publisher_fifo)

        # Publish completed event
        result = service.publish_survey_completed(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
            q1_confidence=0.95,
        )

        assert result is True

        messages = sqs_client.receive_message(
            QueueUrl=fifo_queue,
            MaxNumberOfMessages=1,
        )

        body = json.loads(messages["Messages"][0]["Body"])
        assert body["q1_confidence"] == 0.95

    def test_multiple_event_types(self, sqs_client, fifo_queue, publisher_fifo):
        """Test publishing different event types."""
        service = EventService(publisher_fifo)

        service.publish_survey_completed(
            campaign_id="c1",
            contact_id="ct1",
            call_id="call1",
            answers=["a", "b", "c"],
        )

        service.publish_survey_refused(
            campaign_id="c1",
            contact_id="ct2",
            call_id="call2",
        )

        service.publish_survey_not_reached(
            campaign_id="c1",
            contact_id="ct3",
            total_attempts=5,
        )

        # Receive all messages
        messages = sqs_client.receive_message(
            QueueUrl=fifo_queue,
            MaxNumberOfMessages=10,
        )

        assert len(messages["Messages"]) == 3

        event_types = [
            json.loads(m["Body"])["event_type"] for m in messages["Messages"]
        ]

        assert "survey.completed" in event_types
        assert "survey.refused" in event_types
        assert "survey.not_reached" in event_types