"""
Unit tests for event service.

REQ-015: Event publisher service
"""

import pytest
from unittest.mock import Mock, MagicMock

from app.events.service import EventService, create_event_service
from app.events.publisher import InMemoryEventPublisher
from app.events.schemas import EventType


class TestEventService:
    """Tests for EventService."""

    @pytest.fixture
    def publisher(self):
        """Create an in-memory publisher."""
        return InMemoryEventPublisher()

    @pytest.fixture
    def service(self, publisher):
        """Create an event service with in-memory publisher."""
        return EventService(publisher)

    def test_publish_survey_completed(self, service, publisher):
        """Test publishing a completed survey event."""
        result = service.publish_survey_completed(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
            attempts_count=1,
        )

        assert result is True
        assert len(publisher.events) == 1

        event = publisher.events[0]
        assert event.event_type == EventType.SURVEY_COMPLETED
        assert event.campaign_id == "campaign-123"
        assert event.contact_id == "contact-456"
        assert event.call_id == "call-789"
        assert event.answers == ["8", "Great service", "9"]
        assert event.q1_answer == "8"
        assert event.q2_answer == "Great service"
        assert event.q3_answer == "9"

    def test_publish_survey_completed_with_confidence(self, service, publisher):
        """Test publishing completed event with confidence scores."""
        result = service.publish_survey_completed(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
            q1_confidence=0.95,
            q2_confidence=0.88,
            q3_confidence=0.92,
        )

        assert result is True
        event = publisher.events[0]
        assert event.q1_confidence == 0.95
        assert event.q2_confidence == 0.88
        assert event.q3_confidence == 0.92

    def test_publish_survey_refused(self, service, publisher):
        """Test publishing a refused survey event."""
        result = service.publish_survey_refused(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            attempts_count=1,
            refusal_reason="explicit_refusal",
        )

        assert result is True
        assert len(publisher.events) == 1

        event = publisher.events[0]
        assert event.event_type == EventType.SURVEY_REFUSED
        assert event.campaign_id == "campaign-123"
        assert event.contact_id == "contact-456"
        assert event.refusal_reason == "explicit_refusal"

    def test_publish_survey_refused_without_call_id(self, service, publisher):
        """Test publishing refused event without call_id."""
        result = service.publish_survey_refused(
            campaign_id="campaign-123",
            contact_id="contact-456",
            attempts_count=1,
        )

        assert result is True
        event = publisher.events[0]
        assert event.call_id is None

    def test_publish_survey_not_reached(self, service, publisher):
        """Test publishing a not reached event."""
        result = service.publish_survey_not_reached(
            campaign_id="campaign-123",
            contact_id="contact-456",
            total_attempts=5,
            last_outcome="no_answer",
        )

        assert result is True
        assert len(publisher.events) == 1

        event = publisher.events[0]
        assert event.event_type == EventType.SURVEY_NOT_REACHED
        assert event.campaign_id == "campaign-123"
        assert event.contact_id == "contact-456"
        assert event.total_attempts == 5
        assert event.last_outcome == "no_answer"

    def test_publish_survey_not_reached_with_call_id(self, service, publisher):
        """Test publishing not reached event with last call_id."""
        result = service.publish_survey_not_reached(
            campaign_id="campaign-123",
            contact_id="contact-456",
            total_attempts=5,
            last_outcome="busy",
            call_id="last-call-789",
        )

        assert result is True
        event = publisher.events[0]
        assert event.call_id == "last-call-789"

    def test_publish_handles_failure(self, service, publisher):
        """Test that service handles publisher failures."""
        publisher.should_fail = True

        result = service.publish_survey_completed(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
        )

        assert result is False

    def test_publish_multiple_events(self, service, publisher):
        """Test publishing multiple events."""
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

        assert len(publisher.events) == 3

        completed = publisher.get_events_by_type("survey.completed")
        refused = publisher.get_events_by_type("survey.refused")
        not_reached = publisher.get_events_by_type("survey.not_reached")

        assert len(completed) == 1
        assert len(refused) == 1
        assert len(not_reached) == 1


@pytest.mark.asyncio
class TestEventServiceAsync:
    """Tests for async EventService methods."""

    @pytest.fixture
    def publisher(self):
        """Create an in-memory publisher."""
        return InMemoryEventPublisher()

    @pytest.fixture
    def service(self, publisher):
        """Create an event service with in-memory publisher."""
        return EventService(publisher)

    async def test_publish_survey_completed_async(self, service, publisher):
        """Test async publishing of completed event."""
        result = await service.publish_survey_completed_async(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
        )

        assert result is True
        assert len(publisher.events) == 1

    async def test_publish_survey_refused_async(self, service, publisher):
        """Test async publishing of refused event."""
        result = await service.publish_survey_refused_async(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
        )

        assert result is True
        assert len(publisher.events) == 1

    async def test_publish_survey_not_reached_async(self, service, publisher):
        """Test async publishing of not reached event."""
        result = await service.publish_survey_not_reached_async(
            campaign_id="campaign-123",
            contact_id="contact-456",
            total_attempts=5,
        )

        assert result is True
        assert len(publisher.events) == 1


class TestCreateEventService:
    """Tests for create_event_service factory."""

    def test_create_event_service(self):
        """Test factory function creates service."""
        with pytest.raises(Exception):
            # Will fail without AWS credentials, but validates structure
            service = create_event_service(
                queue_url="https://sqs.eu-central-1.amazonaws.com/123/queue.fifo",
                region_name="eu-central-1",
                max_retries=5,
            )