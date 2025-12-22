"""REQ-013 - LLM contract tests (ASYNC but deterministic).

- NO rete, NO LLM reale
- FakeGateway con risposte hard-coded
- file separato + marker llm_contract
- esegui solo quando vuoi: pytest -q -m llm_contract
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.dialogue.models import CallContext, ConsentState, DialoguePhase, DialogueSession, DialogueSessionState, QuestionState
from app.dialogue.qa import QAOrchestrator, UserIntent


@dataclass
class FakeGateway:
    mode: str = "ok"  # ok | raise

    async def chat_completion(self, messages, system_prompt=None, temperature=0.3, max_tokens=150) -> str:
        if self.mode == "raise":
            raise RuntimeError("boom")

        user_content = (messages[0]["content"] if messages else "").lower()

        # For question delivery: return a deterministic formatted delivery
        if "question to deliver:" in user_content:
            if system_prompt and "repeat" in system_prompt.lower():
                return "Sure — let me repeat the question."
            return "Here is the question."

        # For answer extraction: return deterministic parseable blocks
        if "user response:" in user_content:
            if "repeat" in user_content or "can you repeat" in user_content:
                return "INTENT: REPEAT_REQUEST\nANSWER: NONE\nCONFIDENCE: 0.9\nREASONING: asked to repeat"
            if "blah" in user_content:
                return "INTENT: OFF_TOPIC\nANSWER: NONE\nCONFIDENCE: 0.8\nREASONING: off topic"
            return "INTENT: ANSWER\nANSWER: 7\nCONFIDENCE: 0.95\nREASONING: numeric answer"

        return "INTENT: UNCLEAR\nANSWER: NONE\nCONFIDENCE: 0.1\nREASONING: default"


def _ctx() -> CallContext:
    return CallContext(
        call_id="call-llm",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        language="en",
        intro_script="hi",
        questions=[
            ("Q1 scale?", "scale"),
            ("Q2 free?", "free_text"),
            ("Q3 numeric?", "numeric"),
        ],
        correlation_id="corr",
    )


@pytest.mark.llm_contract
@pytest.mark.anyio
async def test_generate_question_delivery_fallback_on_exception() -> None:
    session = DialogueSession(context=_ctx())
    session.state.phase = DialoguePhase.QUESTION_1
    session.state.consent_state = ConsentState.GRANTED
    session.state.question_states[1] = QuestionState.ASKED

    orch = QAOrchestrator(FakeGateway(mode="raise"))
    delivery = await orch.generate_question_delivery(session, question_number=1, is_repeat=False)

    # fallback: direct question text
    assert delivery.delivery_text == session.get_question_text(1)


@pytest.mark.llm_contract
@pytest.mark.anyio
async def test_process_user_response_parses_repeat_request() -> None:
    session = DialogueSession(
        context=_ctx(),
        state=DialogueSessionState(phase=DialoguePhase.QUESTION_1, consent_state=ConsentState.GRANTED),
    )
    session.state.question_states[1] = QuestionState.ASKED

    orch = QAOrchestrator(FakeGateway(mode="ok"))
    result = await orch.process_user_response(session, "can you repeat the question?")

    assert result.intent == UserIntent.REPEAT_REQUEST
    assert result.answer_text is None
    assert result.confidence >= 0.0


@pytest.mark.llm_contract
@pytest.mark.anyio
async def test_process_user_response_parses_answer_and_handle_answer_advances() -> None:
    session = DialogueSession(
        context=_ctx(),
        state=DialogueSessionState(phase=DialoguePhase.QUESTION_1, consent_state=ConsentState.GRANTED),
    )
    session.state.question_states[1] = QuestionState.ASKED

    orch = QAOrchestrator(FakeGateway(mode="ok"))
    extracted = await orch.process_user_response(session, "7")
    assert extracted.intent == UserIntent.ANSWER
    assert extracted.answer_text == "7"

    next_phase = orch.handle_answer(session, extracted)
    assert next_phase == DialoguePhase.QUESTION_2
    assert session.state.answers[1].answer_text == "7"
