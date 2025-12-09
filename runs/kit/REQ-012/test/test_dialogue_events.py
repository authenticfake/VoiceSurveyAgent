"""
Tests for dialogue event publishing.

REQ-012: Dialogue orchestrator consent flow
"""

from uuid import uuid4

import pytest

from app.dialogue.events import (
    DialogueEvent,
    DialogueEventPublisher,
    DialogueEventType,
)

class MockEventBus:
    """Mock event bus for testing."""

    def __init__(self):
        self.published: list[dict] = []

    async def publish(self, topic: str, message: dict) -> None:
        self.published.append({"topic": topic, "message": message})

@pytest.fixture
def mock_bus() -> MockEventBus:
    """Create mock event bus."""
    return MockEventBus()

@pytest.fixture
def publisher(mock_bus: MockEventBus) -> DialogueEventPublisher:
    """Create event publisher with mock bus."""
    return DialogueEventPublisher(mock_bus)

class TestDialogueEvent:
    """Tests for DialogueEvent."""

    def test_create_event(self) -> None:
        """Test creating dialogue event."""
        event = DialogueEvent(
            event_type=DialogueEventType.SURVEY_REFUSED,
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            payload={"attempts": 1},
        )

        assert event.event_type == DialogueEventType.SURVEY_REFUSED
        assert event.campaign_id == "campaign-123"
        assert event.id is not None
        assert event.timestamp is not None

    def test_to_dict(self) -> None:
        """Test converting event to dictionary."""
        event = DialogueEvent(
            event_type=DialogueEventType.SURVEY_COMPLETED,
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            payload={"answers": ["a", "b", "c"]},
        )

        data = event.to_dict()

        assert data["event_type"] == "survey.completed"
        assert data["campaign_id"] == "campaign-123"
        assert data["contact_id"] == "contact-456"
        assert data["call_id"] == "call-789"
        assert data["payload"]["answers"] == ["a", "b", "c"]
        assert "id" in data
        assert "timestamp" in data

class TestDialogueEventPublisher:
    """Tests for DialogueEventPublisher."""

    @pytest.mark.asyncio
    async def test_publish_refused(
        self,
        publisher: DialogueEventPublisher,
        mock_bus: MockEventBus,
    ) -> None:
        """Test publishing survey.refused event."""
        event = await publisher.publish_refused(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            attempt_count=2,
        )

        assert len(mock_bus.published) == 1
        assert mock_bus.published[0]["topic"] == "survey.events"

        message = mock_bus.published[0]["message"]
        assert message["event_type"] == "survey.refused"
        assert message["campaign_id"] == "campaign-123"
        assert message["contact_id"] == "contact-456"
        assert message["call_id"] == "call-789"
        assert message["payload"]["attempts"] == 2
        assert message["payload"]["reason"] == "explicit_refusal"

    @pytest.mark.asyncio
    async def test_publish_completed(
        self,
        publisher: DialogueEventPublisher,
        mock_bus: MockEventBus,
    ) -> None:
        """Test publishing survey.completed event."""
        event = await publisher.publish_completed(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["answer1", "answer2", "answer3"],
            attempt_count=1,
        )

        assert len(mock_bus.published) == 1
        message = mock_bus.published[0]["message"]
        assert message["event_type"] == "survey.completed"
        assert message["payload"]["answers"] == ["answer1", "answer2", "answer3"]
        assert message["payload"]["attempts"] == 1

    @pytest.mark.asyncio
    async def test_publish_not_reached(
        self,
        publisher: DialogueEventPublisher,
        mock_bus: MockEventBus,
    ) -> None:
        """Test publishing survey.not_reached event."""
        event = await publisher.publish_not_reached(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            attempt_count=5,
        )

        assert len(mock_bus.published) == 1
        message = mock_bus.published[0]["message"]
        assert message["event_type"] == "survey.not_reached"
        assert message["payload"]["attempts"] == 5
        assert message["payload"]["reason"] == "max_attempts_reached"

    @pytest.mark.asyncio
    async def test_event_returned(
        self,
        publisher: DialogueEventPublisher,
        mock_bus: MockEventBus,
    ) -> None:
        """Test that published event is returned."""
        event = await publisher.publish_refused(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            attempt_count=1,
        )

        assert isinstance(event, DialogueEvent)
        assert event.event_type == DialogueEventType.SURVEY_REFUSED
        assert event.campaign_id == "campaign-123"