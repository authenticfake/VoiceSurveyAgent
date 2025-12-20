"""
Tests for DialogueIntegration (SYNC).

REQ-012 constraints:
- synchronous
- fast
- no DB / no SQLAlchemy
"""

from uuid import uuid4

from app.dialogue.integration import DialogueIntegration
from app.dialogue.models import CallContext, ConsentState, DialoguePhase, DialogueSession

def _inject_orchestrator(integration: DialogueIntegration, orch) -> None:
    # Keep it resilient to different internal attribute names
    if hasattr(integration, "orchestrator"):
        setattr(integration, "orchestrator", orch)
        return
    if hasattr(integration, "_orchestrator"):
        setattr(integration, "_orchestrator", orch)
        return
    raise AttributeError("DialogueIntegration has no orchestrator attribute to patch")


class MockLLM:
    async def chat_completion(self, *args, **kwargs):
        return '{"intent": "POSITIVE", "confidence": 0.9}'


class MockTelephony:
    async def play_text(self, *args, **kwargs) -> None:
        return None

    async def terminate_call(self, *args, **kwargs) -> None:
        return None


class MockEventBus:
    async def publish_refused(self, *args, **kwargs) -> None:
        return None

    async def publish_completed(self, *args, **kwargs) -> None:
        return None

    async def publish_not_reached(self, *args, **kwargs) -> None:
        return None


class MockOrchestrator:
    """Sync-friendly mock orchestrator, called by integration async methods."""

    def __init__(self):
        self.call_answered_calls: list[CallContext] = []
        self.user_speech_calls: list[dict] = []
        self.session_by_call_id: dict[str, dict] = {}

    async def handle_call_answered(self, call_context: CallContext):
        self.call_answered_calls.append(call_context)
        session = DialogueSession(call_context=call_context)
        session.phase = DialoguePhase.CONSENT_REQUEST
        session.consent_state = ConsentState.PENDING
        self.session_by_call_id[call_context.call_id] = session
        return session
    
    async def handle_user_response(self, call_id: str, user_response: str, attempt_count: int = 1):
        self.user_speech_calls.append(
            {"call_id": call_id, "user_response": user_response, "attempt_count": attempt_count}
        )
        return {"ok": True}

    def get_session(self, call_id: str):
        return self.session_by_call_id.get(call_id)

    
    


def _ctx(language: str = "en") -> CallContext:
    return CallContext(
        call_id="call-int-1",
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


def test_integration_on_call_answered_routes_to_orchestrator():
    orch = MockOrchestrator()
    integration = DialogueIntegration(
        llm_gateway=MockLLM(),
        telephony_control=MockTelephony(),
        event_bus=MockEventBus(),
    )
    _inject_orchestrator(integration, orch)


    integration.on_call_answered_sync(_ctx())

    assert len(orch.call_answered_calls) == 1
    assert orch.call_answered_calls[0].call_id == "call-int-1"


def test_integration_on_user_speech_routes_to_orchestrator():
    orch = MockOrchestrator()
    integration = DialogueIntegration(
        llm_gateway=MockLLM(),
        telephony_control=MockTelephony(),
        event_bus=MockEventBus(),
    )
    _inject_orchestrator(integration, orch)


    # Create a session first (integration checks orchestrator.get_session)
    integration.on_call_answered_sync(_ctx())

    integration.on_user_speech_sync(
        call_id="call-int-1",
        user_response="yes",
        attempt_count=2,
    )


    assert len(orch.user_speech_calls) == 1
    call = orch.user_speech_calls[0]
    assert call["call_id"] == "call-int-1"
    assert call["user_response"] == "yes"
    assert call["attempt_count"] == 2
