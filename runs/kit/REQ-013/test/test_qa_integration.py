"""
Integration tests for Q&A flow.

REQ-013: Dialogue orchestrator Q&A flow
"""

import pytest
from uuid import uuid4

from app.dialogue.models import (
    CallContext,
    ConsentState,
    DialoguePhase,
    DialogueSession,
    DialogueSessionState,
    QuestionState,
)
from app.dialogue.qa import (
    AnswerResult,
    QAOrchestrator,
    UserIntent,
)


class MockLLMGateway:
    """Mock LLM gateway for integration tests."""

    def __init__(self) -> None:
        self.responses: list[str] = []
        self.call_count = 0

    def set_responses(self, responses: list[str]) -> None:
        """Set the sequence of responses to return."""
        self.responses = responses
        self.call_count = 0

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 150,
    ) -> str:
        """Return the next response in sequence."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return "Default response"


@pytest.fixture
def mock_gateway() -> MockLLMGateway:
    """Create a mock LLM gateway."""
    return MockLLMGateway()


@pytest.fixture
def sample_context() -> CallContext:
    """Create a sample call context."""
    return CallContext(
        call_id="call-integration-test",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        language="en",
        intro_script="Hello, this is a survey.",
        questions=[
            ("On a scale of 1-10, how satisfied are you?", "scale"),
            ("What improvements would you suggest?", "free_text"),
            ("How many times per week do you use our service?", "numeric"),
        ],
        correlation_id="corr-integration",
    )


class TestQAFlowIntegration:
    """Integration tests for complete Q&A flow."""

    @pytest.mark.asyncio
    async def test_complete_qa_flow_all_answers(
        self,
        mock_gateway: MockLLMGateway,
        sample_context: CallContext,
    ) -> None:
        """Test completing all 3 questions successfully."""
        # Setup mock responses
        mock_gateway.set_responses([
            # Q1 delivery
            "On a scale of 1 to 10, how satisfied are you with our service?",
            # Q1 answer extraction
            "INTENT: ANSWER\nANSWER: 8\nCONFIDENCE: 0.95\nREASONING: Clear answer",
            # Q1 acknowledgment
            "Thank you.",
            # Q2 delivery
            "What improvements would you suggest?",
            # Q2 answer extraction
            "INTENT: ANSWER\nANSWER: Better mobile app\nCONFIDENCE: 0.9\nREASONING: Clear suggestion",
            # Q2 acknowledgment
            "Got it.",
            # Q3 delivery
            "How many times per week do you use our service?",
            # Q3 answer extraction
            "INTENT: ANSWER\nANSWER: 5\nCONFIDENCE: 0.92\nREASONING: Clear number",
            # Q3 acknowledgment
            "Thank you.",
            # Completion message
            "Thank you for completing our survey. Goodbye!",
        ])

        session = DialogueSession(
            context=sample_context,
            state=DialogueSessionState(
                phase=DialoguePhase.CONSENT,
                consent_state=ConsentState.GRANTED,
            ),
        )
        orchestrator = QAOrchestrator(mock_gateway)

        # Start Q&A flow
        phase = orchestrator.start_qa_flow(session)
        assert phase == DialoguePhase.QUESTION_1

        # Q1
        delivery = await orchestrator.generate_question_delivery(session, 1)
        assert delivery.question_number == 1

        result = await orchestrator.process_user_response(session, "I'd say 8")
        assert result.intent == UserIntent.ANSWER

        phase = orchestrator.handle_answer(session, result)
        assert phase == DialoguePhase.QUESTION_2

        # Q2
        delivery = await orchestrator.generate_question_delivery(session, 2)
        assert delivery.question_number == 2

        result = await orchestrator.process_user_response(
            session, "The mobile app could be better"
        )
        phase = orchestrator.handle_answer(session, result)
        assert phase == DialoguePhase.QUESTION_3

        # Q3
        delivery = await orchestrator.generate_question_delivery(session, 3)
        assert delivery.question_number == 3

        result = await orchestrator.process_user_response(session, "About 5 times")
        phase = orchestrator.handle_answer(session, result)
        assert phase == DialoguePhase.COMPLETION

        # Verify all answers captured
        assert session.all_questions_answered()
        answers = session.get_all_answers()
        assert len(answers) == 3
        assert answers[0].answer_text == "8"
        assert answers[1].answer_text == "Better mobile app"
        assert answers[2].answer_text == "5"

    @pytest.mark.asyncio
    async def test_qa_flow_with_repeat_request(
        self,
        mock_gateway: MockLLMGateway,
        sample_context: CallContext,
    ) -> None:
        """Test Q&A flow with a repeat request."""
        mock_gateway.set_responses([
            # Q1 delivery
            "How satisfied are you on a scale of 1-10?",
            # Q1 first response - repeat request
            "INTENT: REPEAT_REQUEST\nANSWER: NONE\nCONFIDENCE: 0.9\nREASONING: Asked to repeat",
            # Q1 repeat delivery
            "Let me repeat: How satisfied are you on a scale of 1-10?",
            # Q1 answer after repeat
            "INTENT: ANSWER\nANSWER: 7\nCONFIDENCE: 0.88\nREASONING: Clear answer",
            # Acknowledgment
            "Thank you.",
        ])

        session = DialogueSession(
            context=sample_context,
            state=DialogueSessionState(
                phase=DialoguePhase.CONSENT,
                consent_state=ConsentState.GRANTED,
            ),
        )
        orchestrator = QAOrchestrator(mock_gateway)

        # Start Q&A
        orchestrator.start_qa_flow(session)

        # First delivery
        await orchestrator.generate_question_delivery(session, 1)

        # User asks to repeat
        result = await orchestrator.process_user_response(session, "Sorry, what?")
        assert result.intent == UserIntent.REPEAT_REQUEST

        phase = orchestrator.handle_answer(session, result)
        assert phase == DialoguePhase.QUESTION_1
        assert session.state.repeat_counts[1] == 1
        assert orchestrator.should_repeat_question(session)

        # Repeat delivery
        delivery = await orchestrator.generate_question_delivery(session, 1, is_repeat=True)
        assert delivery.is_repeat

        # Now answer
        result = await orchestrator.process_user_response(session, "Oh, I'd say 7")
        phase = orchestrator.handle_answer(session, result)

        assert phase == DialoguePhase.QUESTION_2
        assert session.state.answers[1].answer_text == "7"
        assert session.state.answers[1].was_repeated

    @pytest.mark.asyncio
    async def test_qa_flow_max_repeats_exceeded(
        self,
        mock_gateway: MockLLMGateway,
        sample_context: CallContext,
    ) -> None:
        """Test that max repeats per question is enforced."""
        mock_gateway.set_responses([
            # Q1 delivery
            "How satisfied are you?",
            # First repeat request
            "INTENT: REPEAT_REQUEST\nANSWER: NONE\nCONFIDENCE: 0.9\nREASONING: Asked to repeat",
            # Second repeat request (should not increment)
            "INTENT: REPEAT_REQUEST\nANSWER: NONE\nCONFIDENCE: 0.9\nREASONING: Asked again",
        ])

        session = DialogueSession(
            context=sample_context,
            state=DialogueSessionState(
                phase=DialoguePhase.CONSENT,
                consent_state=ConsentState.GRANTED,
            ),
        )
        orchestrator = QAOrchestrator(mock_gateway)

        orchestrator.start_qa_flow(session)
        await orchestrator.generate_question_delivery(session, 1)

        # First repeat - allowed
        result = await orchestrator.process_user_response(session, "What?")
        phase = orchestrator.handle_answer(session, result)
        assert session.state.repeat_counts[1] == 1

        # Second repeat - not allowed, stays at 1
        result = await orchestrator.process_user_response(session, "What again?")
        phase = orchestrator.handle_answer(session, result)
        assert session.state.repeat_counts[1] == 1
        assert phase == DialoguePhase.QUESTION_1

    @pytest.mark.asyncio
    async def test_qa_flow_unclear_response_stays_on_question(
        self,
        mock_gateway: MockLLMGateway,
        sample_context: CallContext,
    ) -> None:
        """Test that unclear responses keep user on same question."""
        mock_gateway.set_responses([
            # Q1 delivery
            "How satisfied are you?",
            # Unclear response
            "INTENT: UNCLEAR\nANSWER: NONE\nCONFIDENCE: 0.2\nREASONING: Unintelligible",
            # Clear answer
            "INTENT: ANSWER\nANSWER: 9\nCONFIDENCE: 0.95\nREASONING: Clear",
        ])

        session = DialogueSession(
            context=sample_context,
            state=DialogueSessionState(
                phase=DialoguePhase.CONSENT,
                consent_state=ConsentState.GRANTED,
            ),
        )
        orchestrator = QAOrchestrator(mock_gateway)

        orchestrator.start_qa_flow(session)
        await orchestrator.generate_question_delivery(session, 1)

        # Unclear response
        result = await orchestrator.process_user_response(session, "mumble")
        phase = orchestrator.handle_answer(session, result)
        assert phase == DialoguePhase.QUESTION_1
        assert 1 not in session.state.answers

        # Clear answer
        result = await orchestrator.process_user_response(session, "9 out of 10")
        phase = orchestrator.handle_answer(session, result)
        assert phase == DialoguePhase.QUESTION_2
        assert session.state.answers[1].answer_text == "9"

    @pytest.mark.asyncio
    async def test_qa_flow_italian_language(
        self,
        mock_gateway: MockLLMGateway,
    ) -> None:
        """Test Q&A flow in Italian."""
        context = CallContext(
            call_id="call-italian",
            campaign_id=uuid4(),
            contact_id=uuid4(),
            language="it",
            intro_script="Buongiorno, questo è un sondaggio.",
            questions=[
                ("Quanto è soddisfatto del nostro servizio da 1 a 10?", "scale"),
                ("Cosa potremmo migliorare?", "free_text"),
                ("Quante volte usa il nostro servizio a settimana?", "numeric"),
            ],
        )

        mock_gateway.set_responses([
            # Q1 delivery in Italian
            "Su una scala da 1 a 10, quanto è soddisfatto?",
            # Answer extraction
            "INTENT: ANSWER\nANSWER: 8\nCONFIDENCE: 0.9\nREASONING: Risposta chiara",
        ])

        session = DialogueSession(
            context=context,
            state=DialogueSessionState(
                phase=DialoguePhase.CONSENT,
                consent_state=ConsentState.GRANTED,
            ),
        )
        orchestrator = QAOrchestrator(mock_gateway)

        orchestrator.start_qa_flow(session)
        delivery = await orchestrator.generate_question_delivery(session, 1)

        # Verify Italian question
        assert "soddisfatto" in session.get_question_text(1).lower()

        result = await orchestrator.process_user_response(session, "Direi 8")
        assert result.intent == UserIntent.ANSWER