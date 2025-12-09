"""
Tests for dialogue domain models.

REQ-012: Dialogue orchestrator consent flow
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.dialogue.models import (
    CallContext,
    ConsentState,
    DialoguePhase,
    DialogueSession,
    DialogueSessionState,
)

class TestCallContext:
    """Tests for CallContext."""

    def test_create_valid_context(self) -> None:
        """Test creating valid call context."""
        context = CallContext(
            call_id="test-123",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            call_attempt_id=uuid4(),
            language="en",
            intro_script="Hello, this is a survey.",
            question_1_text="Question 1?",
            question_1_type="scale",
            question_2_text="Question 2?",
            question_2_type="free_text",
            question_3_text="Question 3?",
            question_3_type="numeric",
        )

        assert context.call_id == "test-123"
        assert context.language == "en"

    def test_invalid_language_raises_error(self) -> None:
        """Test that invalid language raises error."""
        with pytest.raises(ValueError, match="Unsupported language"):
            CallContext(
                call_id="test-123",
                campaign_id=uuid4(),
                contact_id=uuid4(),
                call_attempt_id=uuid4(),
                language="fr",  # Not supported
                intro_script="Hello",
                question_1_text="Q1",
                question_1_type="scale",
                question_2_text="Q2",
                question_2_type="free_text",
                question_3_text="Q3",
                question_3_type="numeric",
            )

    def test_empty_intro_raises_error(self) -> None:
        """Test that empty intro script raises error."""
        with pytest.raises(ValueError, match="Intro script is required"):
            CallContext(
                call_id="test-123",
                campaign_id=uuid4(),
                contact_id=uuid4(),
                call_attempt_id=uuid4(),
                language="en",
                intro_script="",
                question_1_text="Q1",
                question_1_type="scale",
                question_2_text="Q2",
                question_2_type="free_text",
                question_3_text="Q3",
                question_3_type="numeric",
            )

    def test_missing_question_raises_error(self) -> None:
        """Test that missing question raises error."""
        with pytest.raises(ValueError, match="All three questions are required"):
            CallContext(
                call_id="test-123",
                campaign_id=uuid4(),
                contact_id=uuid4(),
                call_attempt_id=uuid4(),
                language="en",
                intro_script="Hello",
                question_1_text="Q1",
                question_1_type="scale",
                question_2_text="",  # Empty
                question_2_type="free_text",
                question_3_text="Q3",
                question_3_type="numeric",
            )

class TestDialogueSession:
    """Tests for DialogueSession."""

    def test_create_session_defaults(self) -> None:
        """Test session creation with defaults."""
        session = DialogueSession()

        assert session.phase == DialoguePhase.INTRO
        assert session.state == DialogueSessionState.ACTIVE
        assert session.consent_state == ConsentState.PENDING
        assert session.answers == {}
        assert session.transcript == []
        assert session.started_at is not None

    def test_add_utterance(self) -> None:
        """Test adding utterance to transcript."""
        session = DialogueSession()

        session.add_utterance("agent", "Hello")
        session.add_utterance("user", "Hi")

        assert len(session.transcript) == 2
        assert session.transcript[0]["role"] == "agent"
        assert session.transcript[0]["text"] == "Hello"
        assert session.transcript[1]["role"] == "user"
        assert "timestamp" in session.transcript[0]

    def test_set_consent_granted(self) -> None:
        """Test setting consent as granted."""
        session = DialogueSession()

        session.set_consent_granted()

        assert session.consent_state == ConsentState.GRANTED
        assert session.consent_resolved_at is not None
        assert session.phase == DialoguePhase.QUESTION_1

    def test_set_consent_refused(self) -> None:
        """Test setting consent as refused."""
        session = DialogueSession()

        session.set_consent_refused()

        assert session.consent_state == ConsentState.REFUSED
        assert session.consent_resolved_at is not None
        assert session.phase == DialoguePhase.REFUSED
        assert session.state == DialogueSessionState.REFUSED

    def test_set_answer(self) -> None:
        """Test recording answer."""
        session = DialogueSession()

        session.set_answer(1, "Very satisfied", 0.95)
        session.set_answer(2, "Nothing to improve", 0.8)

        assert session.answers["q1"] == "Very satisfied"
        assert session.answers["q2"] == "Nothing to improve"
        assert session.answer_confidences["q1"] == 0.95
        assert session.answer_confidences["q2"] == 0.8

    def test_mark_completed(self) -> None:
        """Test marking session as completed."""
        session = DialogueSession()

        session.mark_completed()

        assert session.state == DialogueSessionState.COMPLETED
        assert session.phase == DialoguePhase.COMPLETION
        assert session.completed_at is not None

    def test_mark_terminated(self) -> None:
        """Test marking session as terminated."""
        session = DialogueSession()

        session.mark_terminated("timeout")

        assert session.state == DialogueSessionState.TERMINATED
        assert session.phase == DialoguePhase.TERMINATED
        assert session.completed_at is not None
        assert session.metadata["termination_reason"] == "timeout"

class TestDialoguePhase:
    """Tests for DialoguePhase enum."""

    def test_all_phases_defined(self) -> None:
        """Test all required phases are defined."""
        phases = [p.value for p in DialoguePhase]

        assert "intro" in phases
        assert "consent_request" in phases
        assert "consent_processing" in phases
        assert "question_1" in phases
        assert "question_2" in phases
        assert "question_3" in phases
        assert "completion" in phases
        assert "refused" in phases
        assert "terminated" in phases

class TestConsentState:
    """Tests for ConsentState enum."""

    def test_all_states_defined(self) -> None:
        """Test all required states are defined."""
        states = [s.value for s in ConsentState]

        assert "pending" in states
        assert "granted" in states
        assert "refused" in states
        assert "unclear" in states