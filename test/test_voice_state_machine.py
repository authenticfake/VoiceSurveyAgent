import pytest

from app.telephony.webhooks import router as voice_router
from app.dialogue.llm.models import ControlSignal


def _base_state():
    md = {}
    state = voice_router._init_voice_state_if_missing(md)
    return state


def test_consent_refused_ends_call():
    state = _base_state()
    state["current_question"] = 0
    state["phase"] = "consent"

    res = voice_router._apply_llm_to_state(
        state=state,
        assistant_text="Va bene, grazie e arrivederci.",
        signals=[ControlSignal.CONSENT_REFUSED],
        captured_answer=None,
    )

    assert res.end_call is True
    assert res.updated_state["phase"] == "refused"


def test_consent_accepted_moves_to_q1():
    state = _base_state()
    state["current_question"] = 0
    state["phase"] = "consent"

    res = voice_router._apply_llm_to_state(
        state=state,
        assistant_text="Perfetto, iniziamo. Prima domanda...",
        signals=[ControlSignal.CONSENT_ACCEPTED],
        captured_answer=None,
    )

    assert res.end_call is False
    assert res.updated_state["phase"] == "q1"
    assert res.updated_state["current_question"] == 1


def test_answer_captured_stores_answer_for_current_question():
    state = _base_state()
    state["current_question"] = 1
    state["phase"] = "q1"

    res = voice_router._apply_llm_to_state(
        state=state,
        assistant_text="Grazie.",
        signals=[ControlSignal.ANSWER_CAPTURED],
        captured_answer="bene",
    )

    assert res.end_call is False
    assert res.updated_state["collected_answers"][0] == "bene"


def test_move_to_next_question_increments():
    state = _base_state()
    state["current_question"] = 1
    state["phase"] = "q1"
    state["collected_answers"] = ["bene"]

    res = voice_router._apply_llm_to_state(
        state=state,
        assistant_text="Seconda domanda...",
        signals=[ControlSignal.MOVE_TO_NEXT_QUESTION],
        captured_answer=None,
    )

    assert res.end_call is False
    assert res.updated_state["current_question"] == 2
    assert res.updated_state["phase"] == "q2"


def test_survey_complete_ends_call():
    state = _base_state()
    state["current_question"] = 3
    state["phase"] = "q3"
    state["collected_answers"] = ["a1", "a2", "a3"]

    res = voice_router._apply_llm_to_state(
        state=state,
        assistant_text="Grazie per il tempo, arrivederci.",
        signals=[ControlSignal.SURVEY_COMPLETE],
        captured_answer=None,
    )

    assert res.end_call is True
    assert res.updated_state["phase"] == "done"


def test_unclear_or_repeat_is_capped_and_failsafe_ends_after_2():
    state = _base_state()
    state["current_question"] = 1
    state["phase"] = "q1"
    state["reprompt_count"] = 1

    res = voice_router._apply_llm_to_state(
        state=state,
        assistant_text="Mi scusi, può ripetere?",
        signals=[ControlSignal.UNCLEAR_RESPONSE],
        captured_answer=None,
    )

    assert res.end_call is True
    assert res.updated_state["phase"] == "failed"
