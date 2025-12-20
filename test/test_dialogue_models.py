"""
Tests for dialogue domain models (SYNC).

REQ-012 constraints:
- synchronous
- fast
- no DB
"""

from uuid import uuid4

import pytest

from app.dialogue.models import (
    CallContext,
    ConsentState,
    DialoguePhase,
    DialogueSession,
    DialogueSessionState,
)


def _make_call_context(language: str = "en") -> CallContext:
    return CallContext(
        call_id="call-1",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        call_attempt_id=uuid4(),
        language=language,
        intro_script="Hello intro",
        question_1_text="Q1?",
        question_1_type="scale",
        question_2_text="Q2?",
        question_2_type="free_text",
        question_3_text="Q3?",
        question_3_type="numeric",
    )


def test_call_context_validates_language():
    with pytest.raises(ValueError, match="Unsupported language"):
        _make_call_context(language="fr")


def test_call_context_requires_intro_script():
    with pytest.raises(ValueError, match="Intro script is required"):
        CallContext(
            call_id="call-1",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            call_attempt_id=uuid4(),
            language="en",
            intro_script="",
            question_1_text="Q1?",
            question_1_type="scale",
            question_2_text="Q2?",
            question_2_type="free_text",
            question_3_text="Q3?",
            question_3_type="numeric",
        )


def test_call_context_requires_all_questions():
    with pytest.raises(ValueError, match="All three questions are required"):
        CallContext(
            call_id="call-1",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            call_attempt_id=uuid4(),
            language="en",
            intro_script="intro",
            question_1_text="Q1?",
            question_1_type="scale",
            question_2_text="",
            question_2_type="free_text",
            question_3_text="Q3?",
            question_3_type="numeric",
        )


def test_dialogue_session_adds_utterance():
    session = DialogueSession(call_context=_make_call_context())
    assert session.transcript == []

    session.add_utterance(role="agent", text="Hello")
    session.add_utterance(role="user", text="Yes")

    assert len(session.transcript) == 2
    assert session.transcript[0]["role"] == "agent"
    assert session.transcript[0]["text"] == "Hello"
    assert "timestamp" in session.transcript[0]


def test_set_consent_granted_updates_state():
    session = DialogueSession(call_context=_make_call_context())
    assert session.consent_state == ConsentState.PENDING
    assert session.phase == DialoguePhase.INTRO  # default
    assert session.consent_resolved_at is None

    session.set_consent_granted()

    assert session.consent_state == ConsentState.GRANTED
    assert session.phase == DialoguePhase.QUESTION_1
    assert session.consent_resolved_at is not None
    assert session.state == DialogueSessionState.ACTIVE


def test_set_consent_refused_updates_state():
    session = DialogueSession(call_context=_make_call_context())
    session.set_consent_refused()

    assert session.consent_state == ConsentState.REFUSED
    assert session.phase == DialoguePhase.REFUSED
    assert session.state == DialogueSessionState.REFUSED
    assert session.consent_resolved_at is not None
