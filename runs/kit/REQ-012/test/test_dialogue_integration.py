"""
Tests for dialogue integration layer.

REQ-012: Dialogue orchestrator consent flow
"""

from uuid import uuid4

import pytest

from app.dialogue.consent import ConsentIntent
from app.dialogue.integration import DialogueIntegration
from app.dialogue.models import ConsentState, DialoguePhase

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

class MockEventBus:
    """Mock event bus."""

    def __init__(self):
        self.published: list[dict] = []

    async def publish(self, topic: str, message: dict) -> None:
        self.published.append({"topic": topic, "message": message})

@pytest.fixture
def mock_llm() -> MockLLMGateway:
    """Create mock LLM gateway."""
    return MockLLMGateway()

@pytest.fixture
def mock_telephony() -> MockTelephonyControl:
    """Create mock telephony control."""
    return MockTelephonyControl()

@pytest.fixture
def mock_bus() -> MockEventBus:
    """Create mock event bus."""
    return MockEventBus()

@pytest.fixture
def integration(
    mock_llm: MockLLMGateway,
    mock_telephony: MockTelephonyControl,
    mock_bus: MockEventBus,
) -> DialogueIntegration:
    """Create dialogue integration."""
    return DialogueIntegration(mock_llm, mock_telephony, mock_bus)

class TestDialogueIntegration:
    """Tests for DialogueIntegration."""

    @pytest.mark.asyncio
    async def test_on_call_answered(
        self,
        integration: DialogueIntegration,
        mock_telephony: MockTelephonyControl,
    ) -> None:
        """Test handling call.answered event."""
        campaign_id = uuid4()
        contact_id = uuid4()
        call_attempt_id = uuid4()

        session = await integration.on_call_answered(
            call_id="test-call-123",
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_attempt_id=call_attempt_id,
            language="en",
            intro_script="Hello, this is a survey.",
            question_1_text="Question 1?",
            question_1_type="scale",
            question_2_text="Question 2?",
            question_2_type="free_text",
            question_3_text="Question 3?",
            question_3_type="numeric",
        )

        assert session is not None
        assert session.phase == DialoguePhase.CONSENT_REQUEST
        assert len(mock_telephony.played_texts) >= 2

    @pytest.mark.asyncio
    async def test_on_user_speech_positive(
        self,
        mock_llm: MockLLMGateway,
        mock_telephony: MockTelephonyControl,
        mock_bus: MockEventBus,
    ) -> None:
        """Test handling positive consent speech."""
        mock_llm.response = '{"intent": "POSITIVE", "confidence": 0.9}'
        integration = DialogueIntegration(mock_llm, mock_telephony, mock_bus)

        await integration.on_call_answered(
            call_id="test-call-123",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            call_attempt_id=uuid4(),
            language="en",
            intro_script="Hello",
            question_1_text="Q1",
            question_1_type="scale",
            question_2_text="Q2",
            question_2_type="free_text",
            question_3_text="Q3",
            question_3_type="numeric",
        )

        result = await integration.on_user_speech(
            call_id="test-call-123",
            transcript="yes I agree",
        )

        assert result is not None
        assert result.intent == ConsentIntent.POSITIVE

        session = integration.get_session("test-call-123")
        assert session is not None
        assert session.consent_state == ConsentState.GRANTED

    @pytest.mark.asyncio
    async def test_on_user_speech_negative(
        self,
        mock_llm: MockLLMGateway,
        mock_telephony: MockTelephonyControl,
        mock_bus: MockEventBus,
    ) -> None:
        """Test handling negative consent speech."""
        mock_llm.response = '{"intent": "NEGATIVE", "confidence": 0.9}'
        integration = DialogueIntegration(mock_llm, mock_telephony, mock_bus)

        await integration.on_call_answered(
            call_id="test-call-123",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            call_attempt_id=uuid4(),
            language="en",
            intro_script="Hello",
            question_1_text="Q1",
            question_1_type="scale",
            question_2_text="Q2",
            question_2_type="free_text",
            question_3_text="Q3",
            question_3_type="numeric",
        )

        result = await integration.on_user_speech(
            call_id="test-call-123",
            transcript="no thanks",
        )

        assert result is not None
        assert result.intent == ConsentIntent.NEGATIVE
        assert len(mock_telephony.terminated_calls) == 1
        assert len(mock_bus.published) == 1

    @pytest.mark.asyncio
    async def test_on_user_speech_no_session(
        self,
        integration: DialogueIntegration,
    ) -> None:
        """Test handling speech with no session."""
        result = await integration.on_user_speech(
            call_id="unknown-call",
            transcript="yes",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_on_user_speech_not_consent_phase(
        self,
        mock_llm: MockLLMGateway,
        mock_telephony: MockTelephonyControl,
        mock_bus: MockEventBus,
    ) -> None:
        """Test handling speech when not in consent phase."""
        mock_llm.response = '{"intent": "POSITIVE", "confidence": 0.9}'
        integration = DialogueIntegration(mock_llm, mock_telephony, mock_bus)

        await integration.on_call_answered(
            call_id="test-call-123",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            call_attempt_id=uuid4(),
            language="en",
            intro_script="Hello",
            question_1_text="Q1",
            question_1_type="scale",
            question_2_text="Q2",
            question_2_type="free_text",
            question_3_text="Q3",
            question_3_type="numeric",
        )

        # First response grants consent
        await integration.on_user_speech(
            call_id="test-call-123",
            transcript="yes",
        )

        # Second response should return None (not in consent phase)
        result = await integration.on_user_speech(
            call_id="test-call-123",
            transcript="another response",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_session(
        self,
        integration: DialogueIntegration,
    ) -> None:
        """Test session cleanup."""
        await integration.on_call_answered(
            call_id="test-call-123",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            call_attempt_id=uuid4(),
            language="en",
            intro_script="Hello",
            question_1_text="Q1",
            question_1_type="scale",
            question_2_text="Q2",
            question_2_type="free_text",
            question_3_text="Q3",
            question_3_type="numeric",
        )

        assert integration.get_session("test-call-123") is not None

        integration.cleanup_session("test-call-123")

        assert integration.get_session("test-call-123") is None

    @pytest.mark.asyncio
    async def test_correlation_id_passed(
        self,
        integration: DialogueIntegration,
    ) -> None:
        """Test that correlation ID is passed to session."""
        session = await integration.on_call_answered(
            call_id="test-call-123",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            call_attempt_id=uuid4(),
            language="en",
            intro_script="Hello",
            question_1_text="Q1",
            question_1_type="scale",
            question_2_text="Q2",
            question_2_type="free_text",
            question_3_text="Q3",
            question_3_type="numeric",
            correlation_id="corr-123",
        )

        assert session.call_context is not None
        assert session.call_context.correlation_id == "corr-123"