"""
Tests for consent flow orchestration.

REQ-012: Dialogue orchestrator consent flow
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.dialogue.consent import (
    ConsentDetector,
    ConsentFlowOrchestrator,
    ConsentIntent,
    ConsentResult,
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
        self.played_texts.append({
            "call_id": call_id,
            "text": text,
            "language": language,
        })

    async def terminate_call(self, call_id: str, reason: str) -> None:
        self.terminated_calls.append({
            "call_id": call_id,
            "reason": reason,
        })

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
        self.published_events.append({
            "type": "survey.refused",
            "campaign_id": campaign_id,
            "contact_id": contact_id,
            "call_id": call_id,
            "attempt_count": attempt_count,
        })

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
    """Tests for ConsentFlowOrchestrator."""

    @pytest.mark.asyncio
    async def test_handle_call_answered_plays_intro(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that call.answered plays intro script."""
        llm = MockLLMGateway()
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        session = await orchestrator.handle_call_answered(call_context)

        # Verify intro was played
        assert len(mock_telephony.played_texts) >= 1
        assert mock_telephony.played_texts[0]["text"] == call_context.intro_script
        assert mock_telephony.played_texts[0]["language"] == "en"

    @pytest.mark.asyncio
    async def test_handle_call_answered_asks_consent(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that call.answered asks consent question."""
        llm = MockLLMGateway()
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        session = await orchestrator.handle_call_answered(call_context)

        # Verify consent question was asked (second text played)
        assert len(mock_telephony.played_texts) >= 2
        consent_text = mock_telephony.played_texts[1]["text"]
        assert "consent" in consent_text.lower() or "participate" in consent_text.lower()

    @pytest.mark.asyncio
    async def test_handle_call_answered_creates_session(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that call.answered creates dialogue session."""
        llm = MockLLMGateway()
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        session = await orchestrator.handle_call_answered(call_context)

        assert session is not None
        assert session.call_context == call_context
        assert session.phase == DialoguePhase.CONSENT_REQUEST
        assert session.consent_state == ConsentState.PENDING
        assert session.consent_requested_at is not None

    @pytest.mark.asyncio
    async def test_positive_consent_proceeds_to_questions(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that positive consent proceeds to first question."""
        llm = MockLLMGateway('{"intent": "POSITIVE", "confidence": 0.9}')
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(call_context)
        result = await orchestrator.handle_user_response(
            call_id=call_context.call_id,
            user_response="yes, I agree",
        )

        session = orchestrator.get_session(call_context.call_id)
        assert session is not None
        assert session.consent_state == ConsentState.GRANTED
        assert session.phase == DialoguePhase.QUESTION_1
        assert result.intent == ConsentIntent.POSITIVE

    @pytest.mark.asyncio
    async def test_negative_consent_terminates_call(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that negative consent terminates call within 10 seconds."""
        llm = MockLLMGateway('{"intent": "NEGATIVE", "confidence": 0.9}')
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(call_context)
        result = await orchestrator.handle_user_response(
            call_id=call_context.call_id,
            user_response="no thanks",
        )

        # Verify call was terminated
        assert len(mock_telephony.terminated_calls) == 1
        assert mock_telephony.terminated_calls[0]["call_id"] == call_context.call_id
        assert mock_telephony.terminated_calls[0]["reason"] == "consent_refused"

    @pytest.mark.asyncio
    async def test_negative_consent_publishes_event(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that negative consent publishes survey.refused event."""
        llm = MockLLMGateway('{"intent": "NEGATIVE", "confidence": 0.9}')
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(call_context)
        await orchestrator.handle_user_response(
            call_id=call_context.call_id,
            user_response="no thanks",
            attempt_count=2,
        )

        # Verify event was published
        assert len(mock_events.published_events) == 1
        event = mock_events.published_events[0]
        assert event["type"] == "survey.refused"
        assert event["campaign_id"] == str(call_context.campaign_id)
        assert event["contact_id"] == str(call_context.contact_id)
        assert event["call_id"] == call_context.call_id
        assert event["attempt_count"] == 2

    @pytest.mark.asyncio
    async def test_negative_consent_updates_session_state(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that negative consent updates session state correctly."""
        llm = MockLLMGateway('{"intent": "NEGATIVE", "confidence": 0.9}')
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(call_context)
        await orchestrator.handle_user_response(
            call_id=call_context.call_id,
            user_response="no thanks",
        )

        session = orchestrator.get_session(call_context.call_id)
        assert session is not None
        assert session.consent_state == ConsentState.REFUSED
        assert session.phase == DialoguePhase.REFUSED
        assert session.state == DialogueSessionState.REFUSED

    @pytest.mark.asyncio
    async def test_repeat_request_replays_intro(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that repeat request replays intro and consent question."""
        llm = MockLLMGateway('{"intent": "REPEAT_REQUEST", "confidence": 0.8}')
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(call_context)
        initial_count = len(mock_telephony.played_texts)

        await orchestrator.handle_user_response(
            call_id=call_context.call_id,
            user_response="can you repeat that?",
        )

        # Should have played: repeat message, intro, consent question
        assert len(mock_telephony.played_texts) >= initial_count + 3

        session = orchestrator.get_session(call_context.call_id)
        assert session is not None
        assert session.phase == DialoguePhase.CONSENT_REQUEST

    @pytest.mark.asyncio
    async def test_unclear_response_asks_clarification(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that unclear response asks for clarification."""
        llm = MockLLMGateway('{"intent": "UNCLEAR", "confidence": 0.5}')
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(call_context)
        initial_count = len(mock_telephony.played_texts)

        await orchestrator.handle_user_response(
            call_id=call_context.call_id,
            user_response="hmm maybe",
        )

        # Should have played clarification message
        assert len(mock_telephony.played_texts) > initial_count
        last_text = mock_telephony.played_texts[-1]["text"]
        assert "yes or no" in last_text.lower() or "sì o no" in last_text.lower()

    @pytest.mark.asyncio
    async def test_max_unclear_attempts_terminates(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that max unclear attempts terminates call."""
        llm = MockLLMGateway('{"intent": "UNCLEAR", "confidence": 0.5}')
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(call_context)

        # First unclear response
        await orchestrator.handle_user_response(
            call_id=call_context.call_id,
            user_response="hmm",
        )
        assert len(mock_telephony.terminated_calls) == 0

        # Second unclear response - should terminate
        await orchestrator.handle_user_response(
            call_id=call_context.call_id,
            user_response="hmm",
        )
        assert len(mock_telephony.terminated_calls) == 1

    @pytest.mark.asyncio
    async def test_italian_language_messages(
        self,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that Italian language uses Italian messages."""
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

        llm = MockLLMGateway('{"intent": "NEGATIVE", "confidence": 0.9}')
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(context)
        await orchestrator.handle_user_response(
            call_id=context.call_id,
            user_response="no grazie",
        )

        # Verify Italian messages were used
        texts = [t["text"] for t in mock_telephony.played_texts]
        assert any("Acconsente" in t or "Arrivederci" in t for t in texts)

    @pytest.mark.asyncio
    async def test_session_not_found_raises_error(
        self,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that handling response for unknown session raises error."""
        llm = MockLLMGateway()
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        with pytest.raises(ValueError, match="No session found"):
            await orchestrator.handle_user_response(
                call_id="unknown-call",
                user_response="yes",
            )

    @pytest.mark.asyncio
    async def test_transcript_recorded(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test that transcript is recorded during flow."""
        llm = MockLLMGateway('{"intent": "POSITIVE", "confidence": 0.9}')
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(call_context)
        await orchestrator.handle_user_response(
            call_id=call_context.call_id,
            user_response="yes I agree",
        )

        session = orchestrator.get_session(call_context.call_id)
        assert session is not None
        assert len(session.transcript) >= 3  # intro, consent question, user response

        # Verify user response is in transcript
        user_utterances = [t for t in session.transcript if t["role"] == "user"]
        assert len(user_utterances) >= 1
        assert user_utterances[0]["text"] == "yes I agree"

    @pytest.mark.asyncio
    async def test_remove_session(
        self,
        call_context: CallContext,
        mock_telephony: MockTelephonyControl,
        mock_events: MockEventPublisher,
    ) -> None:
        """Test session removal."""
        llm = MockLLMGateway()
        detector = ConsentDetector(llm)
        orchestrator = ConsentFlowOrchestrator(detector, mock_telephony, mock_events)

        await orchestrator.handle_call_answered(call_context)
        assert orchestrator.get_session(call_context.call_id) is not None

        orchestrator.remove_session(call_context.call_id)
        assert orchestrator.get_session(call_context.call_id) is None