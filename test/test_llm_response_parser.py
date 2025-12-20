"""
Unit tests for LLM response parser.

REQ-011: LLM gateway integration
"""

import pytest

from app.dialogue.llm.models import ControlSignal
from app.dialogue.llm.response_parser import (
    parse_llm_response,
    ParsedResponse,
    _infer_signals_from_content,
)

class TestParseResponse:
    """Tests for response parsing."""

    def test_parse_simple_response(self) -> None:
        """Test parsing response without signals."""
        result = parse_llm_response("Hello, how can I help you?")
        assert result.content == "Hello, how can I help you?"
        assert result.signals == []
        assert result.captured_answer is None

    def test_parse_consent_accepted_signal(self) -> None:
        """Test parsing consent accepted signal."""
        response = """Thank you for agreeing to participate!
SIGNAL: CONSENT_ACCEPTED"""
        result = parse_llm_response(response)
        assert "Thank you for agreeing" in result.content
        assert ControlSignal.CONSENT_ACCEPTED in result.signals

    def test_parse_consent_refused_signal(self) -> None:
        """Test parsing consent refused signal."""
        response = """I understand. Thank you for your time.
SIGNAL: CONSENT_REFUSED"""
        result = parse_llm_response(response)
        assert ControlSignal.CONSENT_REFUSED in result.signals

    def test_parse_answer_captured_signal(self) -> None:
        """Test parsing answer captured with value."""
        response = """Thank you for that feedback.
SIGNAL: ANSWER_CAPTURED:8"""
        result = parse_llm_response(response)
        assert ControlSignal.ANSWER_CAPTURED in result.signals
        assert result.captured_answer == "8"

    def test_parse_answer_captured_with_text(self) -> None:
        """Test parsing answer captured with text value."""
        response = """I've noted that.
SIGNAL: ANSWER_CAPTURED:Better customer support"""
        result = parse_llm_response(response)
        assert result.captured_answer == "Better customer support"

    def test_parse_repeat_question_signal(self) -> None:
        """Test parsing repeat question signal."""
        response = """Of course, let me repeat that.
SIGNAL: REPEAT_QUESTION"""
        result = parse_llm_response(response)
        assert ControlSignal.REPEAT_QUESTION in result.signals

    def test_parse_survey_complete_signal(self) -> None:
        """Test parsing survey complete signal."""
        response = """Thank you for completing our survey!
SIGNAL: SURVEY_COMPLETE"""
        result = parse_llm_response(response)
        assert ControlSignal.SURVEY_COMPLETE in result.signals

    def test_parse_unclear_response_signal(self) -> None:
        """Test parsing unclear response signal."""
        response = """I didn't quite catch that. Could you repeat?
SIGNAL: UNCLEAR_RESPONSE"""
        result = parse_llm_response(response)
        assert ControlSignal.UNCLEAR_RESPONSE in result.signals

    def test_parse_multiple_signals(self) -> None:
        """Test parsing multiple signals."""
        response = """Got it, moving on.
SIGNAL: ANSWER_CAPTURED:yes
SIGNAL: MOVE_TO_NEXT_QUESTION"""
        result = parse_llm_response(response)
        assert ControlSignal.ANSWER_CAPTURED in result.signals
        assert ControlSignal.MOVE_TO_NEXT_QUESTION in result.signals

    def test_signal_removed_from_content(self) -> None:
        """Test that signal lines are removed from content."""
        response = """Hello there!
SIGNAL: CONSENT_ACCEPTED
How are you?"""
        result = parse_llm_response(response)
        assert "SIGNAL:" not in result.content
        assert "Hello there!" in result.content
        assert "How are you?" in result.content

    def test_case_insensitive_signal(self) -> None:
        """Test that signal parsing handles case variations."""
        response = """Thank you!
SIGNAL: consent_accepted"""
        result = parse_llm_response(response)
        assert ControlSignal.CONSENT_ACCEPTED in result.signals

class TestInferSignals:
    """Tests for signal inference from content."""

    def test_infer_consent_accepted(self) -> None:
        """Test inferring consent accepted from content."""
        signals = _infer_signals_from_content("Thank you for agreeing to participate!")
        assert ControlSignal.CONSENT_ACCEPTED in signals

    def test_infer_consent_accepted_lets_begin(self) -> None:
        """Test inferring consent from 'let's begin'."""
        signals = _infer_signals_from_content("Great, let's begin with the first question.")
        assert ControlSignal.CONSENT_ACCEPTED in signals

    def test_infer_consent_refused(self) -> None:
        """Test inferring consent refused from content."""
        signals = _infer_signals_from_content("I understand. Thank you for your time. Have a good day.")
        assert ControlSignal.CONSENT_REFUSED in signals

    def test_infer_repeat_question(self) -> None:
        """Test inferring repeat question from content."""
        signals = _infer_signals_from_content("Of course, let me repeat the question for you.")
        assert ControlSignal.REPEAT_QUESTION in signals

    def test_infer_survey_complete(self) -> None:
        """Test inferring survey complete from content."""
        signals = _infer_signals_from_content("Thank you for completing our survey today!")
        assert ControlSignal.SURVEY_COMPLETE in signals

    def test_no_inference_for_neutral_content(self) -> None:
        """Test that neutral content doesn't trigger inference."""
        signals = _infer_signals_from_content("On a scale of 1 to 10, how satisfied are you?")
        assert len(signals) == 0