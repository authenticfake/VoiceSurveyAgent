"""
Unit tests for LLM prompt templates.

REQ-011: LLM gateway integration
"""

import pytest

from app.dialogue.llm.models import SurveyContext
from app.dialogue.llm.prompts import (
    build_system_prompt,
    _get_phase_description,
    _format_collected_answers,
)

class TestBuildSystemPrompt:
    """Tests for system prompt building."""

    @pytest.fixture
    def sample_context(self) -> SurveyContext:
        """Create sample survey context."""
        return SurveyContext(
            campaign_name="Customer Satisfaction Survey",
            language="en",
            intro_script="Hello, I'm calling from Example Corp about a brief survey.",
            question_1_text="On a scale of 1-10, how satisfied are you?",
            question_1_type="scale",
            question_2_text="What could we improve?",
            question_2_type="free_text",
            question_3_text="How likely are you to recommend us?",
            question_3_type="numeric",
        )

    def test_prompt_contains_campaign_name(self, sample_context: SurveyContext) -> None:
        """Test that prompt contains campaign name."""
        prompt = build_system_prompt(sample_context)
        assert "Customer Satisfaction Survey" in prompt

    def test_prompt_contains_language(self, sample_context: SurveyContext) -> None:
        """Test that prompt contains language."""
        prompt = build_system_prompt(sample_context)
        assert "EN" in prompt

    def test_prompt_contains_intro_script(self, sample_context: SurveyContext) -> None:
        """Test that prompt contains intro script."""
        prompt = build_system_prompt(sample_context)
        assert "Example Corp" in prompt

    def test_prompt_contains_questions(self, sample_context: SurveyContext) -> None:
        """Test that prompt contains all questions."""
        prompt = build_system_prompt(sample_context)
        assert "scale of 1-10" in prompt
        assert "could we improve" in prompt
        assert "recommend us" in prompt

    def test_prompt_contains_question_types(self, sample_context: SurveyContext) -> None:
        """Test that prompt contains question types."""
        prompt = build_system_prompt(sample_context)
        assert "scale" in prompt
        assert "free_text" in prompt
        assert "numeric" in prompt

    def test_prompt_contains_phase_for_consent(self, sample_context: SurveyContext) -> None:
        """Test that prompt shows consent phase."""
        sample_context.current_question = 0
        prompt = build_system_prompt(sample_context)
        assert "CONSENT" in prompt

    def test_prompt_contains_phase_for_question(self, sample_context: SurveyContext) -> None:
        """Test that prompt shows question phase."""
        sample_context.current_question = 2
        prompt = build_system_prompt(sample_context)
        assert "QUESTION 2" in prompt

    def test_prompt_contains_collected_answers(self, sample_context: SurveyContext) -> None:
        """Test that prompt shows collected answers."""
        sample_context.current_question = 2
        sample_context.collected_answers = ["8"]
        prompt = build_system_prompt(sample_context)
        assert "Q1: 8" in prompt

    def test_prompt_contains_prohibited_topics(self, sample_context: SurveyContext) -> None:
        """Test that prompt mentions prohibited topics."""
        prompt = build_system_prompt(sample_context)
        assert "Political" in prompt
        assert "Religious" in prompt

    def test_prompt_contains_signal_format(self, sample_context: SurveyContext) -> None:
        """Test that prompt explains signal format."""
        prompt = build_system_prompt(sample_context)
        assert "SIGNAL:" in prompt
        assert "CONSENT_ACCEPTED" in prompt
        assert "ANSWER_CAPTURED" in prompt

class TestGetPhaseDescription:
    """Tests for phase description helper."""

    def test_consent_phase(self) -> None:
        """Test consent phase description."""
        desc = _get_phase_description(0)
        assert "CONSENT" in desc

    def test_question_1_phase(self) -> None:
        """Test question 1 phase description."""
        desc = _get_phase_description(1)
        assert "QUESTION 1" in desc

    def test_question_2_phase(self) -> None:
        """Test question 2 phase description."""
        desc = _get_phase_description(2)
        assert "QUESTION 2" in desc

    def test_question_3_phase(self) -> None:
        """Test question 3 phase description."""
        desc = _get_phase_description(3)
        assert "QUESTION 3" in desc

    def test_completion_phase(self) -> None:
        """Test completion phase description."""
        desc = _get_phase_description(4)
        assert "COMPLETION" in desc

class TestFormatCollectedAnswers:
    """Tests for answer formatting helper."""

    def test_no_answers(self) -> None:
        """Test formatting with no answers."""
        result = _format_collected_answers([])
        assert result == "None yet"

    def test_one_answer(self) -> None:
        """Test formatting with one answer."""
        result = _format_collected_answers(["8"])
        assert "Q1: 8" in result

    def test_multiple_answers(self) -> None:
        """Test formatting with multiple answers."""
        result = _format_collected_answers(["8", "Better support", "9"])
        assert "Q1: 8" in result
        assert "Q2: Better support" in result
        assert "Q3: 9" in result