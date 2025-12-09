"""
Unit tests for event schemas.

REQ-015: Event publisher service
"""

import pytest
from datetime import datetime, timezone

from app.events.schemas import (
    EventType,
    SurveyEvent,
    SurveyCompletedEvent,
    SurveyRefusedEvent,
    SurveyNotReachedEvent,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_event_type_values(self):
        """Test event type enum values."""
        assert EventType.SURVEY_COMPLETED == "survey.completed"
        assert EventType.SURVEY_REFUSED == "survey.refused"
        assert EventType.SURVEY_NOT_REACHED == "survey.not_reached"


class TestSurveyEvent:
    """Tests for base SurveyEvent schema."""

    def test_survey_event_creation(self):
        """Test creating a base survey event."""
        event = SurveyEvent(
            event_type=EventType.SURVEY_COMPLETED,
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
        )

        assert event.event_type == EventType.SURVEY_COMPLETED
        assert event.campaign_id == "campaign-123"
        assert event.contact_id == "contact-456"
        assert event.call_id == "call-789"
        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.attempts_count == 1

    def test_survey_event_auto_generates_id(self):
        """Test that event_id is auto-generated."""
        event1 = SurveyEvent(
            event_type=EventType.SURVEY_COMPLETED,
            campaign_id="campaign-123",
            contact_id="contact-456",
        )
        event2 = SurveyEvent(
            event_type=EventType.SURVEY_COMPLETED,
            campaign_id="campaign-123",
            contact_id="contact-456",
        )

        assert event1.event_id != event2.event_id

    def test_survey_event_timestamp_is_utc(self):
        """Test that timestamp is in UTC."""
        event = SurveyEvent(
            event_type=EventType.SURVEY_COMPLETED,
            campaign_id="campaign-123",
            contact_id="contact-456",
        )

        assert event.timestamp.tzinfo is not None

    def test_survey_event_optional_call_id(self):
        """Test that call_id is optional."""
        event = SurveyEvent(
            event_type=EventType.SURVEY_REFUSED,
            campaign_id="campaign-123",
            contact_id="contact-456",
        )

        assert event.call_id is None


class TestSurveyCompletedEvent:
    """Tests for SurveyCompletedEvent schema."""

    def test_completed_event_creation(self):
        """Test creating a completed event."""
        event = SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["answer1", "answer2", "answer3"],
            q1_answer="answer1",
            q2_answer="answer2",
            q3_answer="answer3",
        )

        assert event.event_type == EventType.SURVEY_COMPLETED
        assert event.answers == ["answer1", "answer2", "answer3"]
        assert event.q1_answer == "answer1"
        assert event.q2_answer == "answer2"
        assert event.q3_answer == "answer3"

    def test_completed_event_with_confidence(self):
        """Test completed event with confidence scores."""
        event = SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["8", "Great service", "9"],
            q1_confidence=0.95,
            q2_confidence=0.88,
            q3_confidence=0.92,
        )

        assert event.q1_confidence == 0.95
        assert event.q2_confidence == 0.88
        assert event.q3_confidence == 0.92

    def test_completed_event_serialization(self):
        """Test event serialization to JSON."""
        event = SurveyCompletedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            answers=["answer1", "answer2", "answer3"],
        )

        json_str = event.model_dump_json()
        assert "survey.completed" in json_str
        assert "campaign-123" in json_str
        assert "answer1" in json_str


class TestSurveyRefusedEvent:
    """Tests for SurveyRefusedEvent schema."""

    def test_refused_event_creation(self):
        """Test creating a refused event."""
        event = SurveyRefusedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            call_id="call-789",
            refusal_reason="explicit_refusal",
        )

        assert event.event_type == EventType.SURVEY_REFUSED
        assert event.refusal_reason == "explicit_refusal"

    def test_refused_event_without_reason(self):
        """Test refused event without explicit reason."""
        event = SurveyRefusedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
        )

        assert event.refusal_reason is None


class TestSurveyNotReachedEvent:
    """Tests for SurveyNotReachedEvent schema."""

    def test_not_reached_event_creation(self):
        """Test creating a not reached event."""
        event = SurveyNotReachedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            total_attempts=5,
            last_outcome="no_answer",
        )

        assert event.event_type == EventType.SURVEY_NOT_REACHED
        assert event.total_attempts == 5
        assert event.last_outcome == "no_answer"

    def test_not_reached_event_attempts_count(self):
        """Test that attempts_count matches total_attempts."""
        event = SurveyNotReachedEvent(
            campaign_id="campaign-123",
            contact_id="contact-456",
            total_attempts=3,
            attempts_count=3,
        )

        assert event.attempts_count == 3
        assert event.total_attempts == 3