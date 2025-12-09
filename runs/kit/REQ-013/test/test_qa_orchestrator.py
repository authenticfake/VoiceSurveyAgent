"""
Tests for Q&A flow orchestration.

REQ-013: Dialogue orchestrator Q&A flow
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.dialogue.models import (
    CallContext,
    ConsentState,
    DialoguePhase,
    DialogueSession,
    DialogueSessionState,
    QuestionAnswer,
    QuestionState,
)
from app.dialogue.qa import (
    AnswerResult,
    QAOrchestrator,
    QuestionDelivery,
    UserIntent,
)


@pytest.fixture
def mock_llm_gateway() -> AsyncMock:
    """Create a mock LLM gateway."""
    gateway = AsyncMock()
    gateway.chat_completion = AsyncMock(return_value="Test response")
    return gateway


@pytest.fixture
def sample_call_context() -> CallContext:
    """Create a sample call context."""
    return CallContext(
        call_id="call-123",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        language="en",
        intro_script="Hello, this is a survey call.",
        questions=[
            ("How satisfied are you with our service on a scale of 1 to 10?", "scale"),
            ("What could we improve?", "free_text"),
            ("How many times per week do you use our product?", "numeric"),
        ],
        correlation_id="corr-123",
    )


@pytest.fixture
def sample_session(sample_call_context: CallContext) -> DialogueSession:
    """Create a sample dialogue session ready for Q&A."""
    state = DialogueSessionState(
        phase=DialoguePhase.QUESTION_1,
        consent_state=ConsentState.GRANTED,
        question_states={
            1: QuestionState.ASKED,
            2: QuestionState.NOT_ASKED,
            3: QuestionState.NOT_ASKED,
        },
    )
    return DialogueSession(context=sample_call_context, state=state)


class TestQAOrchestrator:
    """Tests for QAOrchestrator class."""

    @pytest.mark.asyncio
    async def test_generate_question_delivery_first_question(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test generating delivery for first question."""
        mock_llm_gateway.chat_completion.return_value = (
            "On a scale of 1 to 10, how satisfied are you with our service?"
        )
        orchestrator = QAOrchestrator(mock_llm_gateway)

        delivery = await orchestrator.generate_question_delivery(
            session=sample_session,
            question_number=1,
            is_repeat=False,
        )

        assert delivery.question_number == 1
        assert delivery.question_type == "scale"
        assert delivery.is_repeat is False
        assert "satisfied" in delivery.delivery_text.lower()
        mock_llm_gateway.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_question_delivery_repeat(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test generating delivery for repeated question."""
        mock_llm_gateway.chat_completion.return_value = (
            "Let me repeat that. On a scale of 1 to 10, how satisfied are you?"
        )
        orchestrator = QAOrchestrator(mock_llm_gateway)

        delivery = await orchestrator.generate_question_delivery(
            session=sample_session,
            question_number=1,
            is_repeat=True,
        )

        assert delivery.is_repeat is True
        assert "repeat" in delivery.delivery_text.lower()

    @pytest.mark.asyncio
    async def test_generate_question_delivery_fallback_on_error(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test fallback when LLM fails."""
        mock_llm_gateway.chat_completion.side_effect = Exception("LLM error")
        orchestrator = QAOrchestrator(mock_llm_gateway)

        delivery = await orchestrator.generate_question_delivery(
            session=sample_session,
            question_number=1,
            is_repeat=False,
        )

        # Should fall back to original question text
        assert delivery.question_number == 1
        assert "satisfied" in delivery.delivery_text.lower()

    @pytest.mark.asyncio
    async def test_process_user_response_answer_detected(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test processing a valid answer response."""
        mock_llm_gateway.chat_completion.return_value = """INTENT: ANSWER
ANSWER: 8
CONFIDENCE: 0.95
REASONING: User clearly stated the number 8"""

        orchestrator = QAOrchestrator(mock_llm_gateway)

        result = await orchestrator.process_user_response(
            session=sample_session,
            user_response="I would say about 8",
        )

        assert result.intent == UserIntent.ANSWER
        assert result.answer_text == "8"
        assert result.confidence == 0.95
        assert result.raw_response == "I would say about 8"

    @pytest.mark.asyncio
    async def test_process_user_response_repeat_request(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test detecting a repeat request."""
        mock_llm_gateway.chat_completion.return_value = """INTENT: REPEAT_REQUEST
ANSWER: NONE
CONFIDENCE: 0.9
REASONING: User asked to repeat the question"""

        orchestrator = QAOrchestrator(mock_llm_gateway)

        result = await orchestrator.process_user_response(
            session=sample_session,
            user_response="Can you repeat that please?",
        )

        assert result.intent == UserIntent.REPEAT_REQUEST
        assert result.answer_text is None

    @pytest.mark.asyncio
    async def test_process_user_response_unclear(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test handling unclear response."""
        mock_llm_gateway.chat_completion.return_value = """INTENT: UNCLEAR
ANSWER: NONE
CONFIDENCE: 0.3
REASONING: Response was unintelligible"""

        orchestrator = QAOrchestrator(mock_llm_gateway)

        result = await orchestrator.process_user_response(
            session=sample_session,
            user_response="mumble mumble",
        )

        assert result.intent == UserIntent.UNCLEAR
        assert result.answer_text is None

    @pytest.mark.asyncio
    async def test_process_user_response_outside_qa_phase(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test processing response when not in Q&A phase."""
        sample_session.state.phase = DialoguePhase.CONSENT
        orchestrator = QAOrchestrator(mock_llm_gateway)

        result = await orchestrator.process_user_response(
            session=sample_session,
            user_response="Some response",
        )

        assert result.intent == UserIntent.UNCLEAR
        assert "Not in Q&A phase" in (result.reasoning or "")

    def test_handle_answer_stores_answer(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test that handle_answer stores the answer correctly."""
        orchestrator = QAOrchestrator(mock_llm_gateway)
        answer_result = AnswerResult(
            intent=UserIntent.ANSWER,
            answer_text="8",
            confidence=0.95,
            raw_response="I would say 8",
        )

        next_phase = orchestrator.handle_answer(sample_session, answer_result)

        assert next_phase == DialoguePhase.QUESTION_2
        assert 1 in sample_session.state.answers
        assert sample_session.state.answers[1].answer_text == "8"
        assert sample_session.state.answers[1].confidence == 0.95
        assert sample_session.state.question_states[1] == QuestionState.ANSWERED

    def test_handle_answer_transitions_to_question_2(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test transition from Q1 to Q2."""
        orchestrator = QAOrchestrator(mock_llm_gateway)
        answer_result = AnswerResult(
            intent=UserIntent.ANSWER,
            answer_text="8",
            confidence=0.9,
            raw_response="8",
        )

        next_phase = orchestrator.handle_answer(sample_session, answer_result)

        assert next_phase == DialoguePhase.QUESTION_2
        assert sample_session.state.question_states[2] == QuestionState.ASKED

    def test_handle_answer_transitions_to_question_3(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test transition from Q2 to Q3."""
        sample_session.state.phase = DialoguePhase.QUESTION_2
        sample_session.state.question_states[1] = QuestionState.ANSWERED
        sample_session.state.question_states[2] = QuestionState.ASKED

        orchestrator = QAOrchestrator(mock_llm_gateway)
        answer_result = AnswerResult(
            intent=UserIntent.ANSWER,
            answer_text="Better mobile app",
            confidence=0.85,
            raw_response="I think the mobile app could be better",
        )

        next_phase = orchestrator.handle_answer(sample_session, answer_result)

        assert next_phase == DialoguePhase.QUESTION_3
        assert sample_session.state.question_states[3] == QuestionState.ASKED

    def test_handle_answer_transitions_to_completion(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test transition from Q3 to completion."""
        sample_session.state.phase = DialoguePhase.QUESTION_3
        sample_session.state.question_states[1] = QuestionState.ANSWERED
        sample_session.state.question_states[2] = QuestionState.ANSWERED
        sample_session.state.question_states[3] = QuestionState.ASKED

        orchestrator = QAOrchestrator(mock_llm_gateway)
        answer_result = AnswerResult(
            intent=UserIntent.ANSWER,
            answer_text="5",
            confidence=0.9,
            raw_response="About 5 times a week",
        )

        next_phase = orchestrator.handle_answer(sample_session, answer_result)

        assert next_phase == DialoguePhase.COMPLETION

    def test_handle_answer_repeat_request_allowed(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test that first repeat request is allowed."""
        orchestrator = QAOrchestrator(mock_llm_gateway)
        answer_result = AnswerResult(
            intent=UserIntent.REPEAT_REQUEST,
            answer_text=None,
            confidence=0.9,
            raw_response="Can you repeat that?",
        )

        next_phase = orchestrator.handle_answer(sample_session, answer_result)

        assert next_phase == DialoguePhase.QUESTION_1
        assert sample_session.state.repeat_counts[1] == 1
        assert sample_session.state.question_states[1] == QuestionState.REPEAT_REQUESTED

    def test_handle_answer_repeat_request_max_exceeded(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test that second repeat request stays on question."""
        sample_session.state.repeat_counts[1] = 1  # Already repeated once
        orchestrator = QAOrchestrator(mock_llm_gateway)
        answer_result = AnswerResult(
            intent=UserIntent.REPEAT_REQUEST,
            answer_text=None,
            confidence=0.9,
            raw_response="What was that again?",
        )

        next_phase = orchestrator.handle_answer(sample_session, answer_result)

        # Should stay on same question, not increment repeat count
        assert next_phase == DialoguePhase.QUESTION_1
        assert sample_session.state.repeat_counts[1] == 1

    def test_handle_answer_unclear_stays_on_question(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test that unclear response stays on current question."""
        orchestrator = QAOrchestrator(mock_llm_gateway)
        answer_result = AnswerResult(
            intent=UserIntent.UNCLEAR,
            answer_text=None,
            confidence=0.3,
            raw_response="mumble",
        )

        next_phase = orchestrator.handle_answer(sample_session, answer_result)

        assert next_phase == DialoguePhase.QUESTION_1
        assert sample_session.state.question_states[1] == QuestionState.ASKED

    def test_start_qa_flow(
        self,
        mock_llm_gateway: AsyncMock,
        sample_call_context: CallContext,
    ) -> None:
        """Test starting the Q&A flow."""
        session = DialogueSession(
            context=sample_call_context,
            state=DialogueSessionState(
                phase=DialoguePhase.CONSENT,
                consent_state=ConsentState.GRANTED,
            ),
        )
        orchestrator = QAOrchestrator(mock_llm_gateway)

        next_phase = orchestrator.start_qa_flow(session)

        assert next_phase == DialoguePhase.QUESTION_1
        assert session.state.phase == DialoguePhase.QUESTION_1
        assert session.state.question_states[1] == QuestionState.ASKED

    def test_should_repeat_question_true(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test should_repeat_question returns True when repeat requested."""
        sample_session.state.question_states[1] = QuestionState.REPEAT_REQUESTED
        orchestrator = QAOrchestrator(mock_llm_gateway)

        assert orchestrator.should_repeat_question(sample_session) is True

    def test_should_repeat_question_false(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test should_repeat_question returns False normally."""
        orchestrator = QAOrchestrator(mock_llm_gateway)

        assert orchestrator.should_repeat_question(sample_session) is False

    @pytest.mark.asyncio
    async def test_generate_acknowledgment(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test generating acknowledgment after answer."""
        mock_llm_gateway.chat_completion.return_value = "Thank you for that."
        orchestrator = QAOrchestrator(mock_llm_gateway)
        answer = QuestionAnswer(
            question_number=1,
            question_text="How satisfied are you?",
            answer_text="8",
            confidence=0.9,
        )

        ack = await orchestrator.generate_acknowledgment(sample_session, answer)

        assert ack == "Thank you for that."

    @pytest.mark.asyncio
    async def test_generate_acknowledgment_fallback(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test acknowledgment fallback on LLM error."""
        mock_llm_gateway.chat_completion.side_effect = Exception("LLM error")
        orchestrator = QAOrchestrator(mock_llm_gateway)
        answer = QuestionAnswer(
            question_number=1,
            question_text="How satisfied are you?",
            answer_text="8",
            confidence=0.9,
        )

        ack = await orchestrator.generate_acknowledgment(sample_session, answer)

        assert ack == "Thank you."

    @pytest.mark.asyncio
    async def test_generate_completion_message(
        self,
        mock_llm_gateway: AsyncMock,
        sample_session: DialogueSession,
    ) -> None:
        """Test generating completion message."""
        mock_llm_gateway.chat_completion.return_value = (
            "Thank you for completing our survey. Your feedback is valuable. Goodbye!"
        )
        orchestrator = QAOrchestrator(mock_llm_gateway)

        msg = await orchestrator.generate_completion_message(sample_session)

        assert "thank you" in msg.lower()
        assert "goodbye" in msg.lower()

    @pytest.mark.asyncio
    async def test_generate_completion_message_italian(
        self,
        mock_llm_gateway: AsyncMock,
        sample_call_context: CallContext,
    ) -> None:
        """Test completion message in Italian."""
        sample_call_context.language = "it"
        session = DialogueSession(context=sample_call_context)
        mock_llm_gateway.chat_completion.side_effect = Exception("LLM error")
        orchestrator = QAOrchestrator(mock_llm_gateway)

        msg = await orchestrator.generate_completion_message(session)

        assert "grazie" in msg.lower()


class TestDialogueSession:
    """Tests for DialogueSession model."""

    def test_get_current_question_number(
        self,
        sample_call_context: CallContext,
    ) -> None:
        """Test getting current question number from phase."""
        session = DialogueSession(context=sample_call_context)

        session.state.phase = DialoguePhase.QUESTION_1
        assert session.get_current_question_number() == 1

        session.state.phase = DialoguePhase.QUESTION_2
        assert session.get_current_question_number() == 2

        session.state.phase = DialoguePhase.QUESTION_3
        assert session.get_current_question_number() == 3

        session.state.phase = DialoguePhase.CONSENT
        assert session.get_current_question_number() is None

    def test_get_question_text(
        self,
        sample_call_context: CallContext,
    ) -> None:
        """Test getting question text by number."""
        session = DialogueSession(context=sample_call_context)

        assert "satisfied" in session.get_question_text(1).lower()
        assert "improve" in session.get_question_text(2).lower()
        assert "times" in session.get_question_text(3).lower()

    def test_get_question_text_invalid(
        self,
        sample_call_context: CallContext,
    ) -> None:
        """Test getting question text with invalid number."""
        session = DialogueSession(context=sample_call_context)

        with pytest.raises(ValueError):
            session.get_question_text(0)

        with pytest.raises(ValueError):
            session.get_question_text(4)

    def test_get_question_type(
        self,
        sample_call_context: CallContext,
    ) -> None:
        """Test getting question type by number."""
        session = DialogueSession(context=sample_call_context)

        assert session.get_question_type(1) == "scale"
        assert session.get_question_type(2) == "free_text"
        assert session.get_question_type(3) == "numeric"

    def test_all_questions_answered_false(
        self,
        sample_call_context: CallContext,
    ) -> None:
        """Test all_questions_answered returns False when not all answered."""
        session = DialogueSession(context=sample_call_context)
        session.state.question_states[1] = QuestionState.ANSWERED

        assert session.all_questions_answered() is False

    def test_all_questions_answered_true(
        self,
        sample_call_context: CallContext,
    ) -> None:
        """Test all_questions_answered returns True when all answered."""
        session = DialogueSession(context=sample_call_context)
        session.state.question_states[1] = QuestionState.ANSWERED
        session.state.question_states[2] = QuestionState.ANSWERED
        session.state.question_states[3] = QuestionState.ANSWERED

        assert session.all_questions_answered() is True

    def test_get_all_answers(
        self,
        sample_call_context: CallContext,
    ) -> None:
        """Test getting all answers in order."""
        session = DialogueSession(context=sample_call_context)
        session.state.answers[1] = QuestionAnswer(
            question_number=1,
            question_text="Q1",
            answer_text="A1",
            confidence=0.9,
        )
        session.state.answers[3] = QuestionAnswer(
            question_number=3,
            question_text="Q3",
            answer_text="A3",
            confidence=0.8,
        )

        answers = session.get_all_answers()

        assert len(answers) == 2
        assert answers[0].question_number == 1
        assert answers[1].question_number == 3


class TestAnswerResultParsing:
    """Tests for answer extraction response parsing."""

    def test_parse_valid_answer_response(
        self,
        mock_llm_gateway: AsyncMock,
    ) -> None:
        """Test parsing a valid answer extraction response."""
        orchestrator = QAOrchestrator(mock_llm_gateway)
        llm_response = """INTENT: ANSWER
ANSWER: 8
CONFIDENCE: 0.95
REASONING: User clearly stated the number"""

        result = orchestrator._parse_answer_extraction_response(
            llm_response, "I'd say 8"
        )

        assert result.intent == UserIntent.ANSWER
        assert result.answer_text == "8"
        assert result.confidence == 0.95
        assert result.reasoning == "User clearly stated the number"

    def test_parse_repeat_request_response(
        self,
        mock_llm_gateway: AsyncMock,
    ) -> None:
        """Test parsing a repeat request response."""
        orchestrator = QAOrchestrator(mock_llm_gateway)
        llm_response = """INTENT: REPEAT_REQUEST
ANSWER: NONE
CONFIDENCE: 0.9
REASONING: User asked to repeat"""

        result = orchestrator._parse_answer_extraction_response(
            llm_response, "What was that?"
        )

        assert result.intent == UserIntent.REPEAT_REQUEST
        assert result.answer_text is None

    def test_parse_malformed_response(
        self,
        mock_llm_gateway: AsyncMock,
    ) -> None:
        """Test parsing a malformed response defaults to unclear."""
        orchestrator = QAOrchestrator(mock_llm_gateway)
        llm_response = "This is not in the expected format"

        result = orchestrator._parse_answer_extraction_response(
            llm_response, "some response"
        )

        assert result.intent == UserIntent.UNCLEAR
        assert result.confidence == 0.5

    def test_parse_confidence_clamping(
        self,
        mock_llm_gateway: AsyncMock,
    ) -> None:
        """Test that confidence is clamped to 0-1 range."""
        orchestrator = QAOrchestrator(mock_llm_gateway)
        llm_response = """INTENT: ANSWER
ANSWER: test
CONFIDENCE: 1.5
REASONING: test"""

        result = orchestrator._parse_answer_extraction_response(
            llm_response, "test"
        )

        assert result.confidence == 1.0