"""
Tests for consent detection.

REQ-012: Dialogue orchestrator consent flow
"""

import pytest

from app.dialogue.consent import ConsentDetector, ConsentIntent, ConsentResult

class MockLLMGateway:
    """Mock LLM gateway for testing."""

    def __init__(self, response: str = '{"intent": "POSITIVE", "confidence": 0.9, "reasoning": "test"}'):
        self.response = response
        self.calls: list[dict] = []

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 150,
    ) -> str:
        self.calls.append({
            "messages": messages,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        return self.response

@pytest.fixture
def mock_llm() -> MockLLMGateway:
    """Create mock LLM gateway."""
    return MockLLMGateway()

@pytest.fixture
def detector(mock_llm: MockLLMGateway) -> ConsentDetector:
    """Create consent detector with mock LLM."""
    return ConsentDetector(mock_llm)

class TestConsentDetector:
    """Tests for ConsentDetector."""

    @pytest.mark.asyncio
    async def test_detect_positive_consent(self, mock_llm: MockLLMGateway) -> None:
        """Test detection of positive consent."""
        mock_llm.response = '{"intent": "POSITIVE", "confidence": 0.95, "reasoning": "User said yes"}'
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("yes, I agree", "en")

        assert result.intent == ConsentIntent.POSITIVE
        assert result.confidence == 0.95
        assert result.raw_response == "yes, I agree"
        assert len(mock_llm.calls) == 1

    @pytest.mark.asyncio
    async def test_detect_negative_consent(self, mock_llm: MockLLMGateway) -> None:
        """Test detection of negative consent."""
        mock_llm.response = '{"intent": "NEGATIVE", "confidence": 0.9, "reasoning": "User refused"}'
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("no thanks", "en")

        assert result.intent == ConsentIntent.NEGATIVE
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_detect_unclear_response(self, mock_llm: MockLLMGateway) -> None:
        """Test detection of unclear response."""
        mock_llm.response = '{"intent": "UNCLEAR", "confidence": 0.5, "reasoning": "Mumbling"}'
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("hmm maybe", "en")

        assert result.intent == ConsentIntent.UNCLEAR
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_detect_repeat_request(self, mock_llm: MockLLMGateway) -> None:
        """Test detection of repeat request."""
        mock_llm.response = '{"intent": "REPEAT_REQUEST", "confidence": 0.8, "reasoning": "Asked to repeat"}'
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("can you repeat that?", "en")

        assert result.intent == ConsentIntent.REPEAT_REQUEST

    @pytest.mark.asyncio
    async def test_detect_empty_response(self, detector: ConsentDetector) -> None:
        """Test detection with empty response."""
        result = await detector.detect("", "en")

        assert result.intent == ConsentIntent.UNCLEAR
        assert result.confidence == 1.0
        assert "Empty" in (result.reasoning or "")

    @pytest.mark.asyncio
    async def test_detect_italian_positive(self, mock_llm: MockLLMGateway) -> None:
        """Test detection of Italian positive consent."""
        mock_llm.response = '{"intent": "POSITIVE", "confidence": 0.9, "reasoning": "Italian yes"}'
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("sì, va bene", "it")

        assert result.intent == ConsentIntent.POSITIVE
        # Verify language was passed to LLM
        assert "it" in mock_llm.calls[0]["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_fallback_detection_positive(self, mock_llm: MockLLMGateway) -> None:
        """Test fallback detection for positive keywords."""
        mock_llm.response = "invalid json"
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("yes sure", "en")

        assert result.intent == ConsentIntent.POSITIVE
        assert "fallback" in (result.reasoning or "").lower()

    @pytest.mark.asyncio
    async def test_fallback_detection_negative(self, mock_llm: MockLLMGateway) -> None:
        """Test fallback detection for negative keywords."""
        mock_llm.response = "invalid json"
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("no thanks", "en")

        assert result.intent == ConsentIntent.NEGATIVE

    @pytest.mark.asyncio
    async def test_fallback_detection_italian(self, mock_llm: MockLLMGateway) -> None:
        """Test fallback detection for Italian keywords."""
        mock_llm.response = "invalid json"
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("non mi interessa", "it")

        assert result.intent == ConsentIntent.NEGATIVE

    @pytest.mark.asyncio
    async def test_llm_error_handling(self, mock_llm: MockLLMGateway) -> None:
        """Test handling of LLM errors."""

        async def raise_error(*args, **kwargs):
            raise Exception("LLM unavailable")

        mock_llm.chat_completion = raise_error
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("yes", "en")

        assert result.intent == ConsentIntent.UNCLEAR
        assert "error" in (result.reasoning or "").lower()

    @pytest.mark.asyncio
    async def test_confidence_clamping(self, mock_llm: MockLLMGateway) -> None:
        """Test that confidence is clamped to 0-1 range."""
        mock_llm.response = '{"intent": "POSITIVE", "confidence": 1.5, "reasoning": "test"}'
        detector = ConsentDetector(mock_llm)

        result = await detector.detect("yes", "en")

        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_system_prompt_included(self, mock_llm: MockLLMGateway) -> None:
        """Test that system prompt is included in LLM call."""
        detector = ConsentDetector(mock_llm)

        await detector.detect("yes", "en")

        assert mock_llm.calls[0]["system_prompt"] is not None
        assert "consent" in mock_llm.calls[0]["system_prompt"].lower()