"""
Unit tests for call detail models (REQ-020).

Tests Pydantic model validation and serialization.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.calls.models import (
    CallAttemptOutcome,
    CallDetailResponse,
    TranscriptSnippet,
)


class TestCallAttemptOutcome:
    """Tests for CallAttemptOutcome enum."""
    
    def test_all_outcomes_defined(self):
        """Test all expected outcomes are defined."""
        expected = {"completed", "refused", "no_answer", "busy", "failed"}
        actual = {o.value for o in CallAttemptOutcome}
        assert actual == expected
    
    def test_outcome_values(self):
        """Test outcome enum values match strings."""
        assert CallAttemptOutcome.COMPLETED.value == "completed"
        assert CallAttemptOutcome.REFUSED.value == "refused"
        assert CallAttemptOutcome.NO_ANSWER.value == "no_answer"
        assert CallAttemptOutcome.BUSY.value == "busy"
        assert CallAttemptOutcome.FAILED.value == "failed"


class TestTranscriptSnippet:
    """Tests for TranscriptSnippet model."""
    
    def test_valid_transcript(self):
        """Test valid transcript creation."""
        snippet = TranscriptSnippet(
            text="Hello, this is a survey call...",
            language="en",
            created_at=datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
        )
        assert snippet.text == "Hello, this is a survey call..."
        assert snippet.language == "en"
    
    def test_transcript_serialization(self):
        """Test transcript JSON serialization."""
        snippet = TranscriptSnippet(
            text="Test transcript",
            language="it",
            created_at=datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
        )
        data = snippet.model_dump()
        assert data["text"] == "Test transcript"
        assert data["language"] == "it"
    
    def test_transcript_missing_required_field(self):
        """Test validation error for missing required field."""
        with pytest.raises(ValidationError):
            TranscriptSnippet(
                text="Test",
                # missing language and created_at
            )


class TestCallDetailResponse:
    """Tests for CallDetailResponse model."""
    
    def test_valid_response_minimal(self):
        """Test valid response with minimal fields."""
        response = CallDetailResponse(
            call_id="call-123",
            contact_id=uuid4(),
            campaign_id=uuid4(),
            attempt_number=1,
            outcome=CallAttemptOutcome.COMPLETED,
            started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )
        assert response.call_id == "call-123"
        assert response.attempt_number == 1
        assert response.outcome == CallAttemptOutcome.COMPLETED
        assert response.transcript_snippet is None
        assert response.recording_url is None
    
    def test_valid_response_full(self):
        """Test valid response with all fields."""
        contact_id = uuid4()
        campaign_id = uuid4()
        
        response = CallDetailResponse(
            call_id="call-full",
            contact_id=contact_id,
            campaign_id=campaign_id,
            attempt_number=2,
            provider_call_id="CA123456",
            outcome=CallAttemptOutcome.COMPLETED,
            started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            answered_at=datetime(2024, 1, 15, 10, 30, 15, tzinfo=timezone.utc),
            ended_at=datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
            error_code=None,
            provider_raw_status="completed",
            transcript_snippet=TranscriptSnippet(
                text="Hello...",
                language="en",
                created_at=datetime(2024, 1, 15, 10, 35, 1, tzinfo=timezone.utc),
            ),
            recording_url="https://example.com/recording",
        )
        
        assert response.contact_id == contact_id
        assert response.campaign_id == campaign_id
        assert response.provider_call_id == "CA123456"
        assert response.transcript_snippet is not None
        assert response.recording_url == "https://example.com/recording"
    
    def test_attempt_number_validation(self):
        """Test attempt_number must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            CallDetailResponse(
                call_id="call-invalid",
                contact_id=uuid4(),
                campaign_id=uuid4(),
                attempt_number=0,  # Invalid
                outcome=CallAttemptOutcome.COMPLETED,
                started_at=datetime.now(timezone.utc),
            )
        
        assert "attempt_number" in str(exc_info.value)
    
    def test_response_serialization(self):
        """Test response JSON serialization."""
        contact_id = uuid4()
        campaign_id = uuid4()
        
        response = CallDetailResponse(
            call_id="call-serialize",
            contact_id=contact_id,
            campaign_id=campaign_id,
            attempt_number=1,
            outcome=CallAttemptOutcome.REFUSED,
            started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )
        
        data = response.model_dump(mode="json")
        
        assert data["call_id"] == "call-serialize"
        assert data["contact_id"] == str(contact_id)
        assert data["campaign_id"] == str(campaign_id)
        assert data["outcome"] == "refused"
    
    def test_response_with_failed_outcome(self):
        """Test response with failed outcome and error code."""
        response = CallDetailResponse(
            call_id="call-failed",
            contact_id=uuid4(),
            campaign_id=uuid4(),
            attempt_number=3,
            outcome=CallAttemptOutcome.FAILED,
            started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            error_code="PROVIDER_TIMEOUT",
            provider_raw_status="error",
        )
        
        assert response.outcome == CallAttemptOutcome.FAILED
        assert response.error_code == "PROVIDER_TIMEOUT"
        assert response.provider_raw_status == "error"