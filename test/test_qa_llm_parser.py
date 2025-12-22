"""REQ-013 - LLM prompt + parser robustness (SYNC-ONLY).

Obiettivo:
- testare che i prompt contengano i vincoli chiave
- testare parsing robusto della risposta LLM (formati rotti / intent sconosciuto / confidence clamp)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.dialogue.qa import QAOrchestrator, UserIntent


@dataclass
class _DummyGateway:
    async def chat_completion(self, *args, **kwargs) -> str:  # pragma: no cover
        return ""


def test_build_answer_extraction_prompt_contains_required_format() -> None:
    orch = QAOrchestrator(_DummyGateway())
    p = orch._build_answer_extraction_prompt(language="en", question_type="scale")

    assert "output in this exact format" in p.lower()
    assert "INTENT:" in p
    assert "ANSWER:" in p
    assert "CONFIDENCE:" in p
    assert "REASONING:" in p
    assert "REPEAT_REQUEST" in p


def test_build_question_delivery_prompt_mentions_repeat_when_requested() -> None:
    orch = QAOrchestrator(_DummyGateway())
    p = orch._build_question_delivery_prompt(language="en", question_type="free_text", is_repeat=True)

    assert "repeat" in p.lower()
    assert "Output only the question delivery text" in p


def test_parse_answer_extraction_happy_path() -> None:
    orch = QAOrchestrator(_DummyGateway())
    llm = """INTENT: ANSWER
ANSWER: 8
CONFIDENCE: 0.92
REASONING: user gave a number
"""
    r = orch._parse_answer_extraction_response(llm, raw_user_response="eight")
    assert r.intent == UserIntent.ANSWER
    assert r.answer_text == "8"
    assert abs(r.confidence - 0.92) < 1e-9
    assert r.raw_response == "eight"
    assert r.reasoning is not None


def test_parse_unknown_intent_falls_back_to_unclear() -> None:
    orch = QAOrchestrator(_DummyGateway())
    llm = """INTENT: SKIP
ANSWER: NONE
CONFIDENCE: 0.6
REASONING: user wants to skip
"""
    r = orch._parse_answer_extraction_response(llm, raw_user_response="skip")
    assert r.intent == UserIntent.UNCLEAR
    assert r.answer_text is None


def test_parse_confidence_is_clamped_and_invalid_defaults() -> None:
    orch = QAOrchestrator(_DummyGateway())

    llm_hi = """INTENT: ANSWER
ANSWER: 10
CONFIDENCE: 2.5
REASONING: ok
"""
    r = orch._parse_answer_extraction_response(llm_hi, raw_user_response="10")
    assert r.confidence == 1.0

    llm_lo = """INTENT: ANSWER
ANSWER: 1
CONFIDENCE: -3
REASONING: ok
"""
    r = orch._parse_answer_extraction_response(llm_lo, raw_user_response="1")
    assert r.confidence == 0.0

    llm_bad = """INTENT: ANSWER
ANSWER: 3
CONFIDENCE: not-a-number
REASONING: ok
"""
    r = orch._parse_answer_extraction_response(llm_bad, raw_user_response="3")
    assert r.confidence == 0.5
