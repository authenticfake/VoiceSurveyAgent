"""
Tests for consent flow orchestration.

REQ-012: Dialogue orchestrator consent flow

VINCOLI:
- Test SINCRONI
- Veloci
- No DB / No SQLAlchemy
- Repository in-memory (interno all'orchestrator)
"""

from uuid import uuid4

import pytest

from app.dialogue.consent import (
    ConsentDetector,
    ConsentFlowOrchestrator,
    ConsentIntent,
)
from app.dialogue.models import (
    CallContext,
    ConsentState,
    DialoguePhase,
    DialogueSessionState,
)


class MockLLMGateway:
    """Mock LLM gateway."""

    def __init__(self, response: str = '{"intent": "POSITIVE", "confidence": 0.9}'):
        self.response = response

    async def chat_completion(self, *args, **kwargs) -> str:
        return self.response


class MockTelephonyControl:
    """Mock telephony control."""

    def __init__(self):
        self.played_texts: list[dict] = []
        self.terminated_calls: list[dict] = []

    async def play_text(self, call_id: str, text: str, language: str) -> None:
        self.played_texts.append(
            {
                "call_id": call_id,
                "text": text,
                "language": language,
            }
        )

    async def terminate_call(self, call_id: str, reason: str) -> None:
        self.terminated_calls.append(
            {
                "call_id": call_id,
                "reason": reason,
            }
        )


class MockEventPublisher:
    """Mock event publisher."""

    def __init__(self):
        self.published_events: list[dict] = []

    async def publish_refused(
        self,
        campaign_id: str,
        contact_id: str,
        call_id: str,
        attempt_count: int,
    ) -> None:
        self.published_events.append(
            {
                "type": "survey.refused",
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "call_id": call_id,
                "attempt_count": attempt_count,
            }
        )


@pytest.fixture
def call_context() -> CallContext:
    """Create test call context."""
    return CallContext(
        call_id="test-call-123",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        call_attempt_id=uuid4(),
        language="en",
        intro_script="Hello, this is a survey call from Example Corp.",
        question_1_text="How satisfied are you?",
        question_1_type="scale",
        question_2_text="What could we improve?",
        question_2_type="free_text",
        question_3_text="Would you recommend us?",
        question_3_type="numeric",
    )


@pytest.fixture
def mock_telephony() -> MockTelephonyControl:
    """Create mock telephony control."""
    return MockTelephonyControl()


@pytest.fixture
def mock_events() -> MockEventPublisher:
    """Create mock event publisher."""
    return MockEventPublisher()


class TestConsentFlowOrchestrator:
    """Tests for ConsentFlowOrchestrator (SYNC)."""

    def _make_orchestrator(
        self,
        llm_response: str = '{"intent": "POSITIVE", "confidence": 0.9}',
        telephony: MockTelephonyControl | None = None,
        events: MockEventPublisher | None = None,
    ) -> tuple[ConsentFlowOrchestrator, MockTelephonyControl, MockEventPublisher]:
        telephony = telephony or MockTelephonyControl()
        events = events or MockEventPublisher()

        llm = MockLLMGateway(llm_response)
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, telephony, events)
        return orchestrator, telephony, events

    def test_handle_call_answered_plays_intro(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """call.answered: plays intro immediately."""
        orchestrator, _, _ = self._make_orchestrator(
            telephony=mock_telephony, events=mock_events
        )

        session = orchestrator.handle_call_answered_sync(call_context)

        assert session is not None
        assert len(mock_telephony.played_texts) >= 1
        assert mock_telephony.played_texts[0]["text"] == call_context.intro_script
        assert mock_telephony.played_texts[0]["language"] == "en"

    def test_handle_call_answered_asks_consent(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """call.answered: asks consent question after intro."""
        orchestrator, _, _ = self._make_orchestrator(
            telephony=mock_telephony, events=mock_events
        )

        orchestrator.handle_call_answered_sync(call_context)

        assert len(mock_telephony.played_texts) >= 2
        consent_text = mock_telephony.played_texts[1]["text"].lower()
        assert ("consent" in consent_text) or ("participate" in consent_text)

    def test_handle_call_answered_creates_session(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """call.answered: creates session with expected state."""
        orchestrator, _, _ = self._make_orchestrator(
            telephony=mock_telephony, events=mock_events
        )

        session = orchestrator.handle_call_answered_sync(call_context)

        assert session.call_context == call_context
        assert session.phase == DialoguePhase.CONSENT_REQUEST
        assert session.consent_state == ConsentState.PENDING
        assert session.consent_requested_at is not None

    def test_positive_consent_proceeds_to_questions(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Positive consent: consent granted -> phase QUESTION_1."""
        orchestrator, _, _ = self._make_orchestrator(
            llm_response='{"intent": "POSITIVE", "confidence": 0.9}',
            telephony=mock_telephony,
            events=mock_events,
        )

        orchestrator.handle_call_answered_sync(call_context)
        result = orchestrator.handle_user_response_sync(
            call_id=call_context.call_id,
            user_response="yes, I agree",
        )

        session = orchestrator.get_session(call_context.call_id)
        assert session is not None
        assert session.consent_state == ConsentState.GRANTED
        assert session.phase == DialoguePhase.QUESTION_1
        assert result.intent == ConsentIntent.POSITIVE

    def test_negative_consent_terminates_call_within_10_seconds(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Negative consent: terminate call and enforce timing <= 10s."""
        orchestrator, _, _ = self._make_orchestrator(
            llm_response='{"intent": "NEGATIVE", "confidence": 0.9}',
            telephony=mock_telephony,
            events=mock_events,
        )

        orchestrator.handle_call_answered_sync(call_context)
        orchestrator.handle_user_response_sync(
            call_id=call_context.call_id,
            user_response="no thanks",
        )

        assert len(mock_telephony.terminated_calls) == 1
        assert mock_telephony.terminated_calls[0]["call_id"] == call_context.call_id
        assert mock_telephony.terminated_calls[0]["reason"] == "consent_refused"

        # Timing constraint: refused within 10 seconds from consent request
        session = orchestrator.get_session(call_context.call_id)
        assert session is not None
        assert session.consent_requested_at is not None
        assert session.consent_resolved_at is not None
        delta_seconds = (
            session.consent_resolved_at - session.consent_requested_at
        ).total_seconds()
        assert delta_seconds <= 10.0

    def test_negative_consent_publishes_event(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Negative consent: publishes survey.refused."""
        orchestrator, _, _ = self._make_orchestrator(
            llm_response='{"intent": "NEGATIVE", "confidence": 0.9}',
            telephony=mock_telephony,
            events=mock_events,
        )

        orchestrator.handle_call_answered_sync(call_context)
        orchestrator.handle_user_response_sync(
            call_id=call_context.call_id,
            user_response="no thanks",
            attempt_count=2,
        )

        assert len(mock_events.published_events) == 1
        event = mock_events.published_events[0]
        assert event["type"] == "survey.refused"
        assert event["campaign_id"] == str(call_context.campaign_id)
        assert event["contact_id"] == str(call_context.contact_id)
        assert event["call_id"] == call_context.call_id
        assert event["attempt_count"] == 2

    def test_negative_consent_updates_session_state(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Negative consent: session becomes REFUSED."""
        orchestrator, _, _ = self._make_orchestrator(
            llm_response='{"intent": "NEGATIVE", "confidence": 0.9}',
            telephony=mock_telephony,
            events=mock_events,
        )

        orchestrator.handle_call_answered_sync(call_context)
        orchestrator.handle_user_response_sync(
            call_id=call_context.call_id,
            user_response="no thanks",
        )

        session = orchestrator.get_session(call_context.call_id)
        assert session is not None
        assert session.consent_state == ConsentState.REFUSED
        assert session.phase == DialoguePhase.REFUSED
        assert session.state == DialogueSessionState.REFUSED

    def test_repeat_request_replays_intro_and_consent_question(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Repeat request: should replay intro + consent question."""
        orchestrator, _, _ = self._make_orchestrator(
            llm_response='{"intent": "REPEAT_REQUEST", "confidence": 0.8}',
            telephony=mock_telephony,
            events=mock_events,
        )

        orchestrator.handle_call_answered_sync(call_context)
        initial_count = len(mock_telephony.played_texts)

        orchestrator.handle_user_response_sync(
            call_id=call_context.call_id,
            user_response="can you repeat that?",
        )

        assert len(mock_telephony.played_texts) >= initial_count + 3
        session = orchestrator.get_session(call_context.call_id)
        assert session is not None
        assert session.phase == DialoguePhase.CONSENT_REQUEST

    def test_unclear_response_asks_clarification(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Unclear: ask clarification (yes/no)."""
        orchestrator, _, _ = self._make_orchestrator(
            llm_response='{"intent": "UNCLEAR", "confidence": 0.5}',
            telephony=mock_telephony,
            events=mock_events,
        )

        orchestrator.handle_call_answered_sync(call_context)
        initial_count = len(mock_telephony.played_texts)

        orchestrator.handle_user_response_sync(
            call_id=call_context.call_id,
            user_response="hmm maybe",
        )

        assert len(mock_telephony.played_texts) > initial_count
        last_text = mock_telephony.played_texts[-1]["text"].lower()
        assert ("yes or no" in last_text) or ("sì o no" in last_text)

    def test_max_unclear_attempts_terminates(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """After max unclear attempts: terminate call."""
        orchestrator, _, _ = self._make_orchestrator(
            llm_response='{"intent": "UNCLEAR", "confidence": 0.5}',
            telephony=mock_telephony,
            events=mock_events,
        )

        orchestrator.handle_call_answered_sync(call_context)

        orchestrator.handle_user_response_sync(
            call_id=call_context.call_id,
            user_response="hmm",
        )
        assert len(mock_telephony.terminated_calls) == 0

        orchestrator.handle_user_response_sync(
            call_id=call_context.call_id,
            user_response="hmm",
        )
        assert len(mock_telephony.terminated_calls) == 1

    def test_italian_language_messages(
        self,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Italian language: uses Italian texts."""
        context = CallContext(
            call_id="test-call-it",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            call_attempt_id=uuid4(),
            language="it",
            intro_script="Buongiorno, questa è una chiamata di sondaggio.",
            question_1_text="Quanto è soddisfatto?",
            question_1_type="scale",
            question_2_text="Cosa potremmo migliorare?",
            question_2_type="free_text",
            question_3_text="Ci raccomanderebbe?",
            question_3_type="numeric",
        )

        orchestrator, _, _ = self._make_orchestrator(
            llm_response='{"intent": "NEGATIVE", "confidence": 0.9}',
            telephony=mock_telephony,
            events=mock_events,
        )

        orchestrator.handle_call_answered_sync(context)
        orchestrator.handle_user_response_sync(
            call_id=context.call_id,
            user_response="no grazie",
        )

        texts = [t["text"] for t in mock_telephony.played_texts]
        assert any(("Acconsente" in t) or ("Arrivederci" in t) for t in texts)

    def test_session_not_found_raises_error(
        self,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Unknown session: raise ValueError."""
        orchestrator, _, _ = self._make_orchestrator(
            telephony=mock_telephony, events=mock_events
        )

        with pytest.raises(ValueError, match="No session found"):
            orchestrator.handle_user_response_sync(
                call_id="unknown-call",
                user_response="yes",
            )

    def test_transcript_recorded(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Transcript: includes at least intro, consent question, user response."""
        orchestrator, _, _ = self._make_orchestrator(
            llm_response='{"intent": "POSITIVE", "confidence": 0.9}',
            telephony=mock_telephony,
            events=mock_events,
        )

        orchestrator.handle_call_answered_sync(call_context)
        orchestrator.handle_user_response_sync(
            call_id=call_context.call_id,
            user_response="yes I agree",
        )

        session = orchestrator.get_session(call_context.call_id)
        assert session is not None
        assert len(session.transcript) >= 3

        user_utterances = [t for t in session.transcript if t["role"] == "user"]
        assert len(user_utterances) >= 1
        assert user_utterances[0]["text"] == "yes I agree"

    def test_remove_session(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Session removal."""
        orchestrator, _, _ = self._make_orchestrator(
            telephony=mock_telephony, events=mock_events
        )

        orchestrator.handle_call_answered_sync(call_context)
        assert orchestrator.get_session(call_context.call_id) is not None

        orchestrator.remove_session(call_context.call_id)
        assert orchestrator.get_session(call_context.call_id) is None
