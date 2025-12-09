"""
Unit tests for event publisher.

REQ-015: Event publisher service
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from botocore.exceptions import ClientError

from app.events.publisher import (
    EventPublisher,
    SQSEventPublisher,
    InMemoryEventPublisher,
    EventPublisherConfig,
)
from app.events.schemas import (
    SurveyCompletedEvent,
    SurveyRefusedEvent,
    SurveyNotReachedEvent,
    EventType,
)


class TestEventPublisherConfig:
    """Tests for EventPublisherConfig."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = EventPublisherConfig(queue_url="https://sqs.example.com/queue")

        assert config.region_name == "eu-central-1"
        assert config.max_retries == 3
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 30.0

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = EventPublisherConfig(
            queue_url="https://sqs.example.com/queue",
            region_name="us-west-2",
            max_retries=5,
            base_delay_seconds=0.5,
            max_delay_seconds=60.0,
        )

        assert config.region_name == "us-west-2"
        assert config.max_retries == 5
        assert config.base_delay_seconds == 0.5
        assert config.max_delay_seconds == 60.0


class TestSQSEventPublisher:
    """Tests for SQSEventPublisher."""

    @pytest.fixture
    def mock_sqs_client(self):
        """Create a mock SQS client."""
        return Mock()

    @pytest.fixture
    def publisher(self, mock_sqs_client):
        """Create a publisher with mock client."""
        config = EventPublisherConfig(
            queue_url="https://sqs.eu-central-1.amazonaws.com/123456789/survey-events.fifo",
            max_retries=3,
        )
        return SQSEventPublisher(config, sqs_client=mock_sqs_client)

    @pytest.fixture
    def completed_event(self):
        """Create a sample completed event."""
        return SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
        )

    def test_publish_success(self, publisher, mock_sqs_client, completed_event):
        """Test successful event publishing."""
        mock_sqs_client.send_message.return_value = {
            "MessageId": "msg-123",
            "MD5OfMessageBody": "abc123",
        }

        result = publisher.publish(completed_event)

        assert result is True
        mock_sqs_client.send_message.assert_called_once()

    def test_publish_includes_message_attributes(
        self, publisher, mock_sqs_client, completed_event
    ):
        """Test that message attributes are included."""
        mock_sqs_client.send_message.return_value = {"MessageId": "msg-123"}

        publisher.publish(completed_event)

        call_args = mock_sqs_client.send_message.call_args
        message_attrs = call_args.kwargs["MessageAttributes"]

        assert "event_type" in message_attrs
        assert message_attrs["event_type"]["StringValue"] == "survey.completed"
        assert "campaign_id" in message_attrs
        assert message_attrs["campaign_id"]["StringValue"] == "campaign-123"
        assert "contact_id" in message_attrs
        assert message_attrs["contact_id"]["StringValue"] == "contact-456"
        assert "call_id" in message_attrs
        assert message_attrs["call_id"]["StringValue"] == "call-789"

    def test_publish_fifo_queue_includes_dedup_id(
        self, publisher, mock_sqs_client, completed_event
    ):
        """Test that FIFO queue includes deduplication ID."""
        mock_sqs_client.send_message.return_value = {"MessageId": "msg-123"}

        publisher.publish(completed_event)

        call_args = mock_sqs_client.send_message.call_args
        assert "MessageDeduplicationId" in call_args.kwargs
        assert "MessageGroupId" in call_args.kwargs

    def test_publish_standard_queue_no_dedup_id(self, mock_sqs_client, completed_event):
        """Test that standard queue does not include deduplication ID."""
        config = EventPublisherConfig(
            queue_url="https://sqs.eu-central-1.amazonaws.com/123456789/survey-events",
        )
        publisher = SQSEventPublisher(config, sqs_client=mock_sqs_client)
        mock_sqs_client.send_message.return_value = {"MessageId": "msg-123"}

        publisher.publish(completed_event)

        call_args = mock_sqs_client.send_message.call_args
        assert "MessageDeduplicationId" not in call_args.kwargs
        assert "MessageGroupId" not in call_args.kwargs

    def test_publish_retry_on_failure(self, mock_sqs_client, completed_event):
        """Test retry logic on transient failures."""
        config = EventPublisherConfig(
            queue_url="https://sqs.eu-central-1.amazonaws.com/123456789/survey-events.fifo",
            max_retries=3,
            base_delay_seconds=0.01,  # Fast for testing
        )
        publisher = SQSEventPublisher(config, sqs_client=mock_sqs_client)

        # Fail twice, then succeed
        mock_sqs_client.send_message.side_effect = [
            ClientError(
                {"Error": {"Code": "ServiceUnavailable", "Message": "Temporary"}},
                "SendMessage",
            ),
            ClientError(
                {"Error": {"Code": "ServiceUnavailable", "Message": "Temporary"}},
                "SendMessage",
            ),
            {"MessageId": "msg-123"},
        ]

        result = publisher.publish(completed_event)

        assert result is True
        assert mock_sqs_client.send_message.call_count == 3

    def test_publish_fails_after_max_retries(self, mock_sqs_client, completed_event):
        """Test that publishing fails after max retries."""
        config = EventPublisherConfig(
            queue_url="https://sqs.eu-central-1.amazonaws.com/123456789/survey-events.fifo",
            max_retries=3,
            base_delay_seconds=0.01,
        )
        publisher = SQSEventPublisher(config, sqs_client=mock_sqs_client)

        mock_sqs_client.send_message.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "Temporary"}},
            "SendMessage",
        )

        result = publisher.publish(completed_event)

        assert result is False
        assert mock_sqs_client.send_message.call_count == 3

    def test_deduplication_id_uses_call_id(self, publisher, completed_event):
        """Test that deduplication ID is based on call_id."""
        dedup_id1 = publisher._generate_deduplication_id(completed_event)

        # Same call_id should produce same dedup_id
        event2 = SurveyCompletedEvent(
            campaign_id="different-campaign",
            contact_id="different-contact",
            call_id="call-789",  # Same call_id
            answers=["different"],
        )
        dedup_id2 = publisher._generate_deduplication_id(event2)

        # Different call_id should produce different dedup_id
        event3 = SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="different-call",
            answers=["8", "Great service", "9"],
        )
        dedup_id3 = publisher._generate_deduplication_id(event3)

        assert dedup_id1 == dedup_id2  # Same call_id
        assert dedup_id1 != dedup_id3  # Different call_id

    def test_message_group_id_by_campaign(self, publisher, completed_event):
        """Test that message group ID is based on campaign."""
        group_id = publisher._generate_message_group_id(completed_event)

        assert group_id == "campaign-campaign-123"


class TestInMemoryEventPublisher:
    """Tests for InMemoryEventPublisher."""

    @pytest.fixture
    def publisher(self):
        """Create an in-memory publisher."""
        return InMemoryEventPublisher()

    @pytest.fixture
    def completed_event(self):
        """Create a sample completed event."""
        return SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
        )

    def test_publish_stores_event(self, publisher, completed_event):
        """Test that publish stores the event."""
        result = publisher.publish(completed_event)

        assert result is True
        assert len(publisher.events) == 1
        assert publisher.events[0] == completed_event

    def test_publish_increments_count(self, publisher, completed_event):
        """Test that publish count is incremented."""
        publisher.publish(completed_event)
        publisher.publish(completed_event)

        assert publisher.publish_count == 2

    def test_publish_can_be_configured_to_fail(self, publisher, completed_event):
        """Test that publisher can be configured to fail."""
        publisher.should_fail = True

        result = publisher.publish(completed_event)

        assert result is False
        assert len(publisher.events) == 0
        assert publisher.fail_count == 1

    def test_clear_resets_state(self, publisher, completed_event):
        """Test that clear resets all state."""
        publisher.publish(completed_event)
        publisher.should_fail = True
        publisher.publish(completed_event)

        publisher.clear()

        assert len(publisher.events) == 0
        assert publisher.publish_count == 0
        assert publisher.fail_count == 0

    def test_get_events_by_type(self, publisher):
        """Test filtering events by type."""
        completed = SurveyCompletedEvent(
            campaign_id="c1",
            contact_id="ct1",
            call_id="call1",
            answers=["a"],
        )
        refused = SurveyRefusedEvent(
            campaign_id="c1",
            contact_id="ct2",
            call_id="call2",
        )

        publisher.publish(completed)
        publisher.publish(refused)

        completed_events = publisher.get_events_by_type("survey.completed")
        refused_events = publisher.get_events_by_type("survey.refused")

        assert len(completed_events) == 1
        assert len(refused_events) == 1

    def test_get_events_by_campaign(self, publisher):
        """Test filtering events by campaign."""
        event1 = SurveyCompletedEvent(
            campaign_id="campaign-1",
            contact_id="ct1",
            call_id="call1",
            answers=["a"],
        )
        event2 = SurveyCompletedEvent(
            campaign_id="campaign-2",
            contact_id="ct2",
            call_id="call2",
            answers=["b"],
        )

        publisher.publish(event1)
        publisher.publish(event2)

        campaign1_events = publisher.get_events_by_campaign("campaign-1")

        assert len(campaign1_events) == 1
        assert campaign1_events[0].campaign_id == "campaign-1"

    def test_get_events_by_contact(self, publisher):
        """Test filtering events by contact."""
        event1 = SurveyCompletedEvent(
            campaign_id="c1",
            contact_id="contact-1",
            call_id="call1",
            answers=["a"],
        )
        event2 = SurveyRefusedEvent(
            campaign_id="c1",
            contact_id="contact-1",
            call_id="call2",
        )
        event3 = SurveyCompletedEvent(
            campaign_id="c1",
            contact_id="contact-2",
            call_id="call3",
            answers=["b"],
        )

        publisher.publish(event1)
        publisher.publish(event2)
        publisher.publish(event3)

        contact1_events = publisher.get_events_by_contact("contact-1")

        assert len(contact1_events) == 2


@pytest.mark.asyncio
class TestAsyncPublishing:
    """Tests for async publishing."""

    @pytest.fixture
    def publisher(self):
        """Create an in-memory publisher."""
        return InMemoryEventPublisher()

    @pytest.fixture
    def completed_event(self):
        """Create a sample completed event."""
        return SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
        )

    async def test_publish_async(self, publisher, completed_event):
        """Test async publishing."""
        result = await publisher.publish_async(completed_event)

        assert result is True
        assert len(publisher.events) == 1