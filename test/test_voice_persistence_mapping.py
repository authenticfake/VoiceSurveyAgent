from uuid import uuid4

from app.telephony.webhooks import router as voice_router


class DummyCampaign:
    def __init__(self):
        self.name = "C"
        self.intro_script = "intro"
        self.language = type("L", (), {"value": "it"})()
        self.question_1_text = "Q1?"
        self.question_1_type = type("T", (), {"value": "free_text"})()
        self.question_2_text = "Q2?"
        self.question_2_type = type("T", (), {"value": "free_text"})()
        self.question_3_text = "Q3?"
        self.question_3_type = type("T", (), {"value": "free_text"})()


class DummyAttempt:
    def __init__(self):
        self.id = uuid4()
        self.call_id = "call-123"
        self.campaign_id = uuid4()
        self.contact_id = uuid4()


def test_build_dialogue_session_for_persistence_maps_answers():
    md = {}
    state = voice_router._init_voice_state_if_missing(md)
    state["phase"] = "done"
    state["collected_answers"] = ["a1", "a2", "a3"]

    ds = voice_router._build_dialogue_session_for_persistence(DummyAttempt(), DummyCampaign(), state)

    assert ds.call_context is not None
    assert len(ds.captured_answers) == 3
    assert ds.captured_answers[0].question_index == 1
    assert ds.captured_answers[0].question_text == "Q1?"
    assert ds.captured_answers[0].answer_text == "a1"
    assert ds.captured_answers[2].question_index == 3
    assert ds.captured_answers[2].question_text == "Q3?"
    assert ds.captured_answers[2].answer_text == "a3"
