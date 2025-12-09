"""
Unit tests for CallDetailService (REQ-020).

Tests business logic for call detail retrieval.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from app.calls.exceptions import CallAccessDeniedError, CallNotFoundError
from app.calls.models import CallAttemptOutcome
from app.calls.repository import CallAttemptRecord, CallRepository, TranscriptRecord
from app.calls.service import CallDetailService


class FakeCallRepository:
    """Fake repository for testing."""
    
    def __init__(self):
        self.call_attempts: dict[str, CallAttemptRecord] = {}
        self.transcripts: dict[UUID, TranscriptRecord] = {}
        self.campaign_access: dict[tuple[UUID, UUID], bool] = {}
    
    def add_call_attempt(self, record: CallAttemptRecord) -> None:
        """Add a call attempt to the fake store."""
        self.call_attempts[record.call_id] = record
    
    def add_transcript(self, record: TranscriptRecord) -> None:
        """Add a transcript to the fake store."""
        self.transcripts[record.call_attempt_id] = record
    
    def set_campaign_access(self, campaign_id: UUID, user_id: UUID, has_access: bool) -> None:
        """Set campaign access for a user."""
        self.campaign_access[(campaign_id, user_id)] = has_access
    
    async def get_call_attempt_by_call_id(self, call_id: str) -> Optional[CallAttemptRecord]:
        """Retrieve a call attempt by its call_id."""
        return self.call_attempts.get(call_id)
    
    async def get_transcript_for_call_attempt(self, call_attempt_id: UUID) -> Optional[TranscriptRecord]:
        """Retrieve transcript snippet for a call attempt."""
        return self.transcripts.get(call_attempt_id)
    
    async def check_campaign_access(self, campaign_id: UUID, user_id: UUID) -> bool:
        """Check if user has access to the campaign."""
        return self.campaign_access.get((campaign_id, user_id), True)


def make_call_attempt(
    call_id: str = "call-test-123",
    outcome: str = "completed",
    with_metadata: Optional[dict] = None,
) -> CallAttemptRecord:
    """Factory for creating test call attempts."""
    return CallAttemptRecord(
        id=uuid4(),
        contact_id=uuid4(),
        campaign_id=uuid4(),
        attempt_number=1,
        call_id=call_id,
        provider_call_id="CA123456",
        started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        answered_at=datetime(2024, 1, 15, 10, 30, 15, tzinfo=timezone.utc),
        ended_at=datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
        outcome=outcome,
        provider_raw_status="completed",
        error_code=None,
        metadata=with_metadata or {},
    )


def make_transcript(call_attempt_id: UUID) -> TranscriptRecord:
    """Factory for creating test transcripts."""
    return TranscriptRecord(
        id=uuid4(),
        call_attempt_id=call_attempt_id,
        transcript_text="Hello, this is a survey call about customer satisfaction...",
        language="en",
        created_at=datetime(2024, 1, 15, 10, 35, 1, tzinfo=timezone.utc),
    )


class TestCallDetailService:
    """Tests for CallDetailService."""
    
    @pytest.fixture
    def repository(self) -> FakeCallRepository:
        """Create a fake repository."""
        return FakeCallRepository()
    
    @pytest.fixture
    def service(self, repository: FakeCallRepository) -> CallDetailService:
        """Create service with fake repository."""
        return CallDetailService(repository)
    
    @pytest.mark.asyncio
    async def test_get_call_detail_success(
        self, service: CallDetailService, repository: FakeCallRepository
    ):
        """Test successful retrieval of call details."""
        # Arrange
        call_attempt = make_call_attempt(call_id="call-success-001")
        repository.add_call_attempt(call_attempt)
        user_id = uuid4()
        
        # Act
        result = await service.get_call_detail("call-success-001", user_id)
        
        # Assert
        assert result.call_id == "call-success-001"
        assert result.contact_id == call_attempt.contact_id
        assert result.campaign_id == call_attempt.campaign_id
        assert result.attempt_number == 1
        assert result.outcome == CallAttemptOutcome.COMPLETED
        assert result.provider_call_id == "CA123456"
        assert result.transcript_snippet is None
        assert result.recording_url is None
    
    @pytest.mark.asyncio
    async def test_get_call_detail_with_transcript(
        self, service: CallDetailService, repository: FakeCallRepository
    ):
        """Test retrieval includes transcript when available."""
        # Arrange
        call_attempt = make_call_attempt(call_id="call-with-transcript")
        repository.add_call_attempt(call_attempt)
        transcript = make_transcript(call_attempt.id)
        repository.add_transcript(transcript)
        user_id = uuid4()
        
        # Act
        result = await service.get_call_detail("call-with-transcript", user_id)
        
        # Assert
        assert result.transcript_snippet is not None
        assert result.transcript_snippet.text == transcript.transcript_text
        assert result.transcript_snippet.language == "en"
    
    @pytest.mark.asyncio
    async def test_get_call_detail_with_recording_url(
        self, service: CallDetailService, repository: FakeCallRepository
    ):
        """Test retrieval includes recording URL from metadata."""
        # Arrange
        call_attempt = make_call_attempt(
            call_id="call-with-recording",
            with_metadata={"recording_url": "https://recordings.example.com/abc123"},
        )
        repository.add_call_attempt(call_attempt)
        user_id = uuid4()
        
        # Act
        result = await service.get_call_detail("call-with-recording", user_id)
        
        # Assert
        assert result.recording_url == "https://recordings.example.com/abc123"
    
    @pytest.mark.asyncio
    async def test_get_call_detail_not_found(
        self, service: CallDetailService, repository: FakeCallRepository
    ):
        """Test CallNotFoundError raised for non-existent call."""
        # Arrange
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(CallNotFoundError) as exc_info:
            await service.get_call_detail("non-existent-call", user_id)
        
        assert exc_info.value.call_id == "non-existent-call"
    
    @pytest.mark.asyncio
    async def test_get_call_detail_access_denied(
        self, service: CallDetailService, repository: FakeCallRepository
    ):
        """Test CallAccessDeniedError when user lacks campaign access."""
        # Arrange
        call_attempt = make_call_attempt(call_id="call-restricted")
        repository.add_call_attempt(call_attempt)
        user_id = uuid4()
        repository.set_campaign_access(call_attempt.campaign_id, user_id, False)
        
        # Act & Assert
        with pytest.raises(CallAccessDeniedError) as exc_info:
            await service.get_call_detail("call-restricted", user_id)
        
        assert exc_info.value.call_id == "call-restricted"
    
    @pytest.mark.asyncio
    async def test_get_call_detail_all_outcomes(
        self, service: CallDetailService, repository: FakeCallRepository
    ):
        """Test all possible call outcomes are handled."""
        user_id = uuid4()
        
        for outcome in ["completed", "refused", "no_answer", "busy", "failed"]:
            # Arrange
            call_id = f"call-{outcome}"
            call_attempt = make_call_attempt(call_id=call_id, outcome=outcome)
            repository.add_call_attempt(call_attempt)
            
            # Act
            result = await service.get_call_detail(call_id, user_id)
            
            # Assert
            assert result.outcome.value == outcome
    
    @pytest.mark.asyncio
    async def test_get_call_detail_with_error_code(
        self, service: CallDetailService, repository: FakeCallRepository
    ):
        """Test retrieval includes error code for failed calls."""
        # Arrange
        call_attempt = make_call_attempt(call_id="call-failed", outcome="failed")
        call_attempt.error_code = "PROVIDER_TIMEOUT"
        call_attempt.provider_raw_status = "error"
        repository.add_call_attempt(call_attempt)
        user_id = uuid4()
        
        # Act
        result = await service.get_call_detail("call-failed", user_id)
        
        # Assert
        assert result.outcome == CallAttemptOutcome.FAILED
        assert result.error_code == "PROVIDER_TIMEOUT"
        assert result.provider_raw_status == "error"