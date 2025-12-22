"""REQ-013 - Q&A flow: extra sync edge-cases.

Questo file esisteva come "integration" async (LLM). Per i vincoli del progetto,
i test di logica devono essere 100% sincroni e senza dipendenze esterne.

Qui teniamo solo edge-case di state handling che completano la copertura degli
acceptance criteria, senza duplicare l'intera suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.dialogue.models import CallContext, ConsentState, DialoguePhase, DialogueSession
from app.dialogue.qa import AnswerResult, QAOrchestrator, UserIntent


@dataclass
class _DummyGateway:
    async def chat_completion(self, *args, **kwargs) -> str:  # pragma: no cover
        return ""


def _ctx() -> CallContext:
    return CallContext(
        call_id="call-edge",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        language="en",
        intro_script="hi",
        questions=[
            ("Q1?", "free_text"),
            ("Q2?", "free_text"),
            ("Q3?", "free_text"),
        ],
        correlation_id=None,
    )


def test_handle_answer_outside_qa_phase_is_noop() -> None:
    """Defensive: if called outside Q&A, do not mutate phase."""
    session = DialogueSession(context=_ctx())
    session.state.phase = DialoguePhase.INTRO
    session.state.consent_state = ConsentState.GRANTED

    orch = QAOrchestrator(_DummyGateway())
    phase = orch.handle_answer(
        session,
        AnswerResult(intent=UserIntent.ANSWER, answer_text="x", confidence=1.0, raw_response="x"),
    )

    assert phase == DialoguePhase.INTRO
    assert session.state.phase == DialoguePhase.INTRO
