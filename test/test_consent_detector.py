"""
Tests for ConsentDetector (SYNC).

REQ-012:
- Consent intent detection
- JSON parsing from LLM
- Keyword fallback
"""

from app.dialogue.consent import (
    ConsentDetector,
    ConsentIntent,
)


class MockLLM:
    """Mock LLM returning a fixed response."""

    def __init__(self, response: str):
        self.response = response

    async def chat_completion(self, *args, **kwargs) -> str:
        return self.response


def test_detect_positive_from_json():
    llm = MockLLM('{"intent": "POSITIVE", "confidence": 0.95}')
    detector = ConsentDetector(llm)

    result = detector.detect_sync(
        user_response="yes",
        language="en",
    )

    assert result.intent == ConsentIntent.POSITIVE
    assert result.confidence >= 0.9


def test_detect_negative_from_json():
    llm = MockLLM('{"intent": "NEGATIVE", "confidence": 0.8}')
    detector = ConsentDetector(llm)

    result = detector.detect_sync(
        user_response="no",
        language="en",
    )

    assert result.intent == ConsentIntent.NEGATIVE
    assert result.confidence >= 0.7


def test_detect_fallback_positive_keyword():
    llm = MockLLM("this is not json at all")
    detector = ConsentDetector(llm)

    result = detector.detect_sync(
        user_response="yes I agree",
        language="en",
    )

    assert result.intent == ConsentIntent.POSITIVE


def test_detect_fallback_negative_keyword():
    llm = MockLLM("garbage output")
    detector = ConsentDetector(llm)

    result = detector.detect_sync(
        user_response="no thanks",
        language="en",
    )

    assert result.intent == ConsentIntent.NEGATIVE


def test_detect_fallback_italian_positive():
    llm = MockLLM("nonsense")
    detector = ConsentDetector(llm)

    result = detector.detect_sync(
        user_response="sì certo",
        language="it",
    )

    assert result.intent == ConsentIntent.POSITIVE


def test_detect_fallback_italian_negative():
    llm = MockLLM("???")
    detector = ConsentDetector(llm)

    result = detector.detect_sync(
        user_response="no grazie",
        language="it",
    )

    assert result.intent == ConsentIntent.NEGATIVE


def test_detect_unclear_when_no_match():
    llm = MockLLM("invalid")
    detector = ConsentDetector(llm)

    result = detector.detect_sync(
        user_response="maybe later",
        language="en",
    )

    assert result.intent == ConsentIntent.UNCLEAR
