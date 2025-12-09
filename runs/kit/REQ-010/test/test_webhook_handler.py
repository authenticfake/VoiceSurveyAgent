"""
Unit tests for webhook handler.

REQ-010: Telephony webhook handler
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.calls.models import CallAttempt, CallOutcome
from app.contacts.models import ContactState
from app.telephony.events import CallEvent, CallEventType
from app.telephony.webhooks.handler import WebhookHandler

@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session

@pytest.fixture
def mock_dialogue_starter() -> AsyncMock:
    """Create mock dialogue starter."""
    starter = AsyncMock()
    starter.start_dialogue = AsyncMock()
    return starter

@pytest.fixture
def sample_call_attempt() -> CallAttempt:
    """Create sample call attempt."""
    attempt = MagicMock(spec=CallAttempt)
    attempt.id = uuid4()
    attempt.call_id = "test-call-123"
    attempt.contact_id = uuid4()
    attempt.campaign_id = uuid4()
    attempt.attempt_number = 1
    attempt.metadata = {}
    attempt.outcome = None
    attempt.provider_raw_status = None
    attempt.answered_at = None
    attempt.ended_at = None
    attempt.error_code = None
    return attempt

@pytest.fixture
def sample_answered_event(sample_call_attempt: CallAttempt) -> CallEvent:
    """Create sample call.answered event."""
    return CallEvent(
        event_type=CallEventType.ANSWERED,
        call_id=sample_call_attempt.call_id,
        provider_call_id="CA123456",
        campaign_id=sample_call_attempt.campaign_id,
        contact_id=sample_call_attempt.contact_id,
        timestamp=datetime.utcnow(),
        raw_status="in-progress",
    )

@pytest.fixture
def sample_no_answer_event(sample_call_attempt: CallAttempt) -> CallEvent:
    """Create sample call.no_answer event."""
    return CallEvent(
        event_type=CallEventType.NO_ANSWER,
        call_id=sample_call_attempt.call_id,
        provider_call_id="CA123456",
        campaign_id=sample_call_attempt.campaign_id,
        contact_id=sample_call_attempt.contact_id,
        timestamp=datetime.utcnow(),
        raw_status="no-answer",
    )

@pytest.fixture
def sample_busy_event(sample_call_attempt: CallAttempt) -> CallEvent:
    """Create sample call.busy event."""
    return CallEvent(
        event_type=CallEventType.BUSY,
        call_id=sample_call_attempt.call_id,
        provider_call_id="CA123456",
        campaign_id=sample_call_attempt.campaign_id,
        contact_id=sample_call_attempt.contact_id,
        timestamp=datetime.utcnow(),
        raw_status="busy",
    )

@pytest.fixture
def sample_failed_event(sample_call_attempt: CallAttempt) -> CallEvent:
    """Create sample call.failed event."""
    return CallEvent(
        event_type=CallEventType.FAILED,
        call_id=sample_call_attempt.call_id,
        provider_call_id="CA123456",
        campaign_id=sample_call_attempt.campaign_id,
        contact_id=sample_call_attempt.contact_id,
        timestamp=datetime.utcnow(),
        raw_status="failed",
        error_code="30003",
        error_message="Call rejected",
    )

class TestWebhookHandler:
    """Tests for WebhookHandler."""

    @pytest.mark.asyncio
    async def test_handle_answered_event_triggers_dialogue(
        self,
        mock_session: AsyncMock,
        mock_dialogue_starter: AsyncMock,
        sample_call_attempt: CallAttempt,
        sample_answered_event: CallEvent,
    ) -> None:
        """Test that call.answered triggers dialogue start."""
        # Setup mock to return call attempt
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_call_attempt
        mock_session.execute.return_value = mock_result

        handler = WebhookHandler(
            session=mock_session,
            dialogue_starter=mock_dialogue_starter,
        )

        result = await handler.handle_event(sample_answered_event)

        assert result is True
        mock_dialogue_starter.start_dialogue.assert_called_once_with(
            call_id=sample_answered_event.call_id,
            campaign_id=sample_answered_event.campaign_id,
            contact_id=sample_answered_event.contact_id,
        )
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_no_answer_updates_state(
        self,
        mock_session: AsyncMock,
        sample_call_attempt: CallAttempt,
        sample_no_answer_event: CallEvent,
    ) -> None:
        """Test that call.no_answer updates attempt outcome and contact state."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_call_attempt
        mock_session.execute.return_value = mock_result

        handler = WebhookHandler(session=mock_session)

        result = await handler.handle_event(sample_no_answer_event)

        assert result is True
        assert sample_call_attempt.outcome == CallOutcome.NO_ANSWER
        assert sample_call_attempt.ended_at == sample_no_answer_event.timestamp
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_busy_updates_state(
        self,
        mock_session: AsyncMock,
        sample_call_attempt: CallAttempt,
        sample_busy_event: CallEvent,
    ) -> None:
        """Test that call.busy updates attempt outcome and contact state."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_call_attempt
        mock_session.execute.return_value = mock_result

        handler = WebhookHandler(session=mock_session)

        result = await handler.handle_event(sample_busy_event)

        assert result is True
        assert sample_call_attempt.outcome == CallOutcome.BUSY
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_failed_logs_error(
        self,
        mock_session: AsyncMock,
        sample_call_attempt: CallAttempt,
        sample_failed_event: CallEvent,
    ) -> None:
        """Test that call.failed logs error and updates state."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_call_attempt
        mock_session.execute.return_value = mock_result

        handler = WebhookHandler(session=mock_session)

        result = await handler.handle_event(sample_failed_event)

        assert result is True
        assert sample_call_attempt.outcome == CallOutcome.FAILED
        assert sample_call_attempt.error_code == "30003"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_event_skipped(
        self,
        mock_session: AsyncMock,
        sample_call_attempt: CallAttempt,
        sample_answered_event: CallEvent,
    ) -> None:
        """Test that duplicate events are handled idempotently."""
        # Mark event as already processed
        sample_call_attempt.metadata = {
            "processed_events": [CallEventType.ANSWERED.value]
        }

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_call_attempt
        mock_session.execute.return_value = mock_result

        handler = WebhookHandler(session=mock_session)

        result = await handler.handle_event(sample_answered_event)

        assert result is False
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_call_attempt_returns_false(
        self,
        mock_session: AsyncMock,
        sample_answered_event: CallEvent,
    ) -> None:
        """Test that missing call attempt returns False."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        handler = WebhookHandler(session=mock_session)

        result = await handler.handle_event(sample_answered_event)

        assert result is False
        mock_session.commit.assert_not_called()