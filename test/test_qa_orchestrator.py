"""REQ-013 - Q&A flow orchestration (SYNC-ONLY).

Vincoli rispettati:
- test di logica SINCRONI
- velocissimi
- senza DB / SQLAlchemy
- repository/state in-memory (DialogueSession)
- niente asyncio/await nei test

Nota: i sorgenti includono anche metodi async (LLM), ma qui testiamo solo la
state-machine e la gestione della sessione (core acceptance REQ-013).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.dialogue.models import (
    CallContext,
    ConsentState,
    DialoguePhase,
    DialogueSession,
    DialogueSessionState,
    QuestionState,
)
from app.dialogue.qa import AnswerResult, QAOrchestrator, UserIntent


@dataclass
class _DummyGateway:
    """LLM gateway dummy.

    QAOrchestrator richiede un oggetto con `chat_completion` async, ma questi test
    non chiamano mai i metodi async. Tenerlo minimale evita dipendenze/mocking
    e mantiene i test sync-only.
    """

    async def chat_completion(  # pragma: no cover
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 150,
    ) -> str:
        return ""


@pytest.fixture()
def sample_call_context() -> CallContext:
    return CallContext(
        call_id="call-123",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        language="en",
        intro_script="Hello, this is a survey call.",
        questions=[
            ("How satisfied are you with our service on a scale of 1 to 10?", "scale"),
            ("What could we improve?", "free_text"),
            ("How many times per week do you use our product?", "numeric"),
        ],
        correlation_id="corr-123",
    )


@pytest.fixture()
def session_in_q1(sample_call_context: CallContext) -> DialogueSession:
    state = DialogueSessionState(
        phase=DialoguePhase.QUESTION_1,
        consent_state=ConsentState.GRANTED,
        question_states={
            1: QuestionState.ASKED,
            2: QuestionState.NOT_ASKED,
            3: QuestionState.NOT_ASKED,
        },
    )
    return DialogueSession(context=sample_call_context, state=state)


def test_question_text_is_sourced_from_campaign_config(sample_call_context: CallContext) -> None:
    """AC: question text comes from campaign config."""
    session = DialogueSession(context=sample_call_context)

    assert session.get_question_text(1) == sample_call_context.questions[0][0]
    assert session.get_question_text(2) == sample_call_context.questions[1][0]
    assert session.get_question_text(3) == sample_call_context.questions[2][0]

    with pytest.raises(ValueError):
        session.get_question_text(0)
    with pytest.raises(ValueError):
        session.get_question_text(4)


def test_start_qa_flow_sets_q1_and_marks_asked(sample_call_context: CallContext) -> None:
    """AC: after consent granted, Q&A starts at Q1 and marks it asked."""
    session = DialogueSession(
        context=sample_call_context,
        state=DialogueSessionState(phase=DialoguePhase.CONSENT, consent_state=ConsentState.GRANTED),
    )

    orch = QAOrchestrator(_DummyGateway())
    next_phase = orch.start_qa_flow(session)

    assert next_phase == DialoguePhase.QUESTION_1
    assert session.state.phase == DialoguePhase.QUESTION_1
    assert session.state.question_states[1] == QuestionState.ASKED


def test_answer_q1_is_captured_as_draft_and_transitions_to_q2(session_in_q1: DialogueSession) -> None:
    """AC: capture answer in draft + transition Q1 -> Q2."""
    orch = QAOrchestrator(_DummyGateway())
    result = AnswerResult(
        intent=UserIntent.ANSWER,
        answer_text="8",
        confidence=0.95,
        raw_response="I'd say 8",
    )

    next_phase = orch.handle_answer(session_in_q1, result)

    assert next_phase == DialoguePhase.QUESTION_2
    assert session_in_q1.state.phase == DialoguePhase.QUESTION_2

    # Draft state (in-memory) capture
    assert session_in_q1.state.answers[1].answer_text == "8"
    assert session_in_q1.state.answers[1].confidence == 0.95
    assert session_in_q1.state.question_states[1] == QuestionState.ANSWERED
    assert session_in_q1.state.question_states[2] == QuestionState.ASKED


def test_repeat_request_is_allowed_once_and_is_not_infinite_loop(session_in_q1: DialogueSession) -> None:
    """AC: repeat request is allowed only once per question."""
    orch = QAOrchestrator(_DummyGateway())

    # First repeat request: allowed and marked
    repeat_1 = AnswerResult(
        intent=UserIntent.REPEAT_REQUEST,
        answer_text=None,
        confidence=0.9,
        raw_response="Sorry, can you repeat?",
    )
    phase_1 = orch.handle_answer(session_in_q1, repeat_1)
    assert phase_1 == DialoguePhase.QUESTION_1
    assert session_in_q1.state.repeat_counts[1] == 1
    assert orch.should_repeat_question(session_in_q1) is True

    # Second repeat request: must NOT increment beyond 1
    repeat_2 = AnswerResult(
        intent=UserIntent.REPEAT_REQUEST,
        answer_text=None,
        confidence=0.9,
        raw_response="Again please?",
    )
    phase_2 = orch.handle_answer(session_in_q1, repeat_2)
    assert phase_2 == DialoguePhase.QUESTION_1
    assert session_in_q1.state.repeat_counts[1] == 1


def test_three_answers_required_before_completion(sample_call_context: CallContext) -> None:
    """AC: completion only after 3 answers."""
    session = DialogueSession(
        context=sample_call_context,
        state=DialogueSessionState(phase=DialoguePhase.QUESTION_1, consent_state=ConsentState.GRANTED),
    )
    session.state.question_states[1] = QuestionState.ASKED

    orch = QAOrchestrator(_DummyGateway())

    # Q1 -> Q2
    phase = orch.handle_answer(
        session,
        AnswerResult(intent=UserIntent.ANSWER, answer_text="8", confidence=0.9, raw_response="8"),
    )
    assert phase == DialoguePhase.QUESTION_2

    # Q2 -> Q3
    phase = orch.handle_answer(
        session,
        AnswerResult(intent=UserIntent.ANSWER, answer_text="Better UX", confidence=0.8, raw_response="Better UX"),
    )
    assert phase == DialoguePhase.QUESTION_3
    assert session.state.phase == DialoguePhase.QUESTION_3

    # Q3 -> COMPLETION
    phase = orch.handle_answer(
        session,
        AnswerResult(intent=UserIntent.ANSWER, answer_text="5", confidence=0.85, raw_response="5"),
    )
    assert phase == DialoguePhase.COMPLETION
    assert session.state.phase == DialoguePhase.COMPLETION

    assert session.all_questions_answered() is True
    assert len(session.get_all_answers()) == 3

def test_empty_answer_does_not_advance(session_in_q1: DialogueSession) -> None:
    """Edge-case: risposta vuota -> non avanza (resta su Q corrente)."""
    orch = QAOrchestrator(_DummyGateway())
    result = AnswerResult(
        intent=UserIntent.ANSWER,
        answer_text="",  # empty -> should not be treated as a valid answer
        confidence=0.9,
        raw_response="",
    )

    phase = orch.handle_answer(session_in_q1, result)

    assert phase == DialoguePhase.QUESTION_1
    assert session_in_q1.state.phase == DialoguePhase.QUESTION_1
    assert 1 not in session_in_q1.state.answers
    # state should remain "asked" (or still be repeat_requested depending on previous actions)
    assert session_in_q1.state.question_states[1] in (QuestionState.ASKED, QuestionState.REPEAT_REQUESTED)


def test_repeat_then_answer_sets_was_repeated_true_and_advances(session_in_q1: DialogueSession) -> None:
    """Edge-case: repeat_counts==1 e poi arriva risposta -> was_repeated True + avanza."""
    orch = QAOrchestrator(_DummyGateway())

    # request repeat once
    repeat = AnswerResult(
        intent=UserIntent.REPEAT_REQUEST,
        answer_text=None,
        confidence=0.9,
        raw_response="repeat",
    )
    phase = orch.handle_answer(session_in_q1, repeat)
    assert phase == DialoguePhase.QUESTION_1
    assert session_in_q1.state.repeat_counts[1] == 1

    # then answer
    ans = AnswerResult(
        intent=UserIntent.ANSWER,
        answer_text="7",
        confidence=0.9,
        raw_response="7",
    )
    phase = orch.handle_answer(session_in_q1, ans)

    assert phase == DialoguePhase.QUESTION_2
    assert session_in_q1.state.answers[1].answer_text == "7"
    assert session_in_q1.state.answers[1].was_repeated is True


def test_unclear_or_offtopic_does_not_advance(session_in_q1: DialogueSession) -> None:
    """Edge-case: UNCLEAR / OFF_TOPIC -> non avanza."""
    orch = QAOrchestrator(_DummyGateway())

    unclear = AnswerResult(
        intent=UserIntent.UNCLEAR,
        answer_text=None,
        confidence=0.2,
        raw_response="huh?",
    )
    phase = orch.handle_answer(session_in_q1, unclear)
    assert phase == DialoguePhase.QUESTION_1
    assert session_in_q1.state.phase == DialoguePhase.QUESTION_1

    off_topic = AnswerResult(
        intent=UserIntent.OFF_TOPIC,
        answer_text=None,
        confidence=0.7,
        raw_response="by the way what's the time?",
    )
    phase = orch.handle_answer(session_in_q1, off_topic)
    assert phase == DialoguePhase.QUESTION_1
    assert session_in_q1.state.phase == DialoguePhase.QUESTION_1


def test_double_answer_overwrites_and_advances(sample_call_context: CallContext) -> None:
    """Edge-case: double answer su stessa domanda -> overwrite deterministico e avanza."""
    session = DialogueSession(
        context=sample_call_context,
        state=DialogueSessionState(phase=DialoguePhase.QUESTION_1, consent_state=ConsentState.GRANTED),
    )
    session.state.question_states[1] = QuestionState.ASKED

    orch = QAOrchestrator(_DummyGateway())

    a1 = AnswerResult(intent=UserIntent.ANSWER, answer_text="6", confidence=0.7, raw_response="6")
    phase = orch.handle_answer(session, a1)
    assert phase == DialoguePhase.QUESTION_2
    assert session.state.answers[1].answer_text == "6"

    # Simula scenario "still on Q1" (es: retry / reprocess): riportiamo la fase a Q1
    session.state.phase = DialoguePhase.QUESTION_1
    session.state.question_states[1] = QuestionState.ASKED

    a2 = AnswerResult(intent=UserIntent.ANSWER, answer_text="9", confidence=0.9, raw_response="9")
    phase = orch.handle_answer(session, a2)
    assert phase == DialoguePhase.QUESTION_2
    assert session.state.answers[1].answer_text == "9"  # overwrite
