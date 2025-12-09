"""
Q&A flow orchestration for survey questions.

REQ-013: Dialogue orchestrator Q&A flow
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from app.dialogue.models import (
    CallContext,
    DialoguePhase,
    DialogueSession,
    DialogueSessionState,
    QuestionAnswer,
    QuestionState,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


class UserIntent(str, Enum):
    """Detected user intent from response."""

    ANSWER = "answer"  # User provided an answer
    REPEAT_REQUEST = "repeat_request"  # User asks to repeat the question
    UNCLEAR = "unclear"  # Cannot determine intent
    OFF_TOPIC = "off_topic"  # User response is off-topic


@dataclass
class AnswerResult:
    """Result of answer extraction from user response."""

    intent: UserIntent
    answer_text: str | None
    confidence: float
    raw_response: str
    reasoning: str | None = None


@dataclass
class QuestionDelivery:
    """Question delivery with natural language formatting."""

    question_number: int
    question_text: str
    question_type: str
    delivery_text: str
    is_repeat: bool = False


class LLMGatewayProtocol(Protocol):
    """Protocol for LLM gateway integration."""

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 150,
    ) -> str:
        """Generate a chat completion.

        Args:
            messages: Conversation messages.
            system_prompt: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.

        Returns:
            Generated response text.
        """
        ...


class QAOrchestrator:
    """Orchestrates the Q&A flow for survey questions.

    Handles:
    - Sequential question delivery (Q1 -> Q2 -> Q3)
    - Answer capture and validation
    - Repeat request detection and handling (max 1 repeat per question)
    - State transitions between questions
    """

    MAX_REPEATS_PER_QUESTION = 1

    def __init__(self, llm_gateway: LLMGatewayProtocol) -> None:
        """Initialize the Q&A orchestrator.

        Args:
            llm_gateway: LLM gateway for natural language processing.
        """
        self._llm_gateway = llm_gateway

    async def generate_question_delivery(
        self,
        session: DialogueSession,
        question_number: int,
        is_repeat: bool = False,
    ) -> QuestionDelivery:
        """Generate natural language delivery for a question.

        Args:
            session: Current dialogue session.
            question_number: Question number (1-3).
            is_repeat: Whether this is a repeat of the question.

        Returns:
            Question delivery with formatted text.
        """
        question_text = session.get_question_text(question_number)
        question_type = session.get_question_type(question_number)
        language = session.context.language

        system_prompt = self._build_question_delivery_prompt(
            language=language,
            question_type=question_type,
            is_repeat=is_repeat,
        )

        messages = [
            {
                "role": "user",
                "content": f"Question to deliver: {question_text}",
            }
        ]

        try:
            delivery_text = await self._llm_gateway.chat_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=200,
            )
            delivery_text = delivery_text.strip()
        except Exception as e:
            logger.error(
                f"LLM error generating question delivery: {e}",
                extra={
                    "call_id": session.context.call_id,
                    "question_number": question_number,
                },
            )
            # Fallback to direct question text
            if is_repeat:
                delivery_text = f"Let me repeat the question: {question_text}"
            else:
                delivery_text = question_text

        logger.info(
            f"Generated question delivery for Q{question_number}",
            extra={
                "call_id": session.context.call_id,
                "is_repeat": is_repeat,
                "question_type": question_type,
            },
        )

        return QuestionDelivery(
            question_number=question_number,
            question_text=question_text,
            question_type=question_type,
            delivery_text=delivery_text,
            is_repeat=is_repeat,
        )

    async def process_user_response(
        self,
        session: DialogueSession,
        user_response: str,
    ) -> AnswerResult:
        """Process user response to extract answer or detect intent.

        Args:
            session: Current dialogue session.
            user_response: Raw user response text.

        Returns:
            Answer result with extracted answer or detected intent.
        """
        question_number = session.get_current_question_number()
        if question_number is None:
            logger.warning(
                "process_user_response called outside Q&A phase",
                extra={"call_id": session.context.call_id, "phase": session.state.phase},
            )
            return AnswerResult(
                intent=UserIntent.UNCLEAR,
                answer_text=None,
                confidence=0.0,
                raw_response=user_response,
                reasoning="Not in Q&A phase",
            )

        question_text = session.get_question_text(question_number)
        question_type = session.get_question_type(question_number)
        language = session.context.language

        system_prompt = self._build_answer_extraction_prompt(
            language=language,
            question_type=question_type,
        )

        messages = [
            {
                "role": "user",
                "content": f"Question asked: {question_text}\n\nUser response: {user_response}",
            }
        ]

        try:
            llm_response = await self._llm_gateway.chat_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=300,
            )
            result = self._parse_answer_extraction_response(llm_response, user_response)
        except Exception as e:
            logger.error(
                f"LLM error processing user response: {e}",
                extra={
                    "call_id": session.context.call_id,
                    "question_number": question_number,
                },
            )
            result = AnswerResult(
                intent=UserIntent.UNCLEAR,
                answer_text=None,
                confidence=0.0,
                raw_response=user_response,
                reasoning=f"LLM error: {str(e)}",
            )

        logger.info(
            f"Processed user response for Q{question_number}",
            extra={
                "call_id": session.context.call_id,
                "intent": result.intent.value,
                "confidence": result.confidence,
            },
        )

        return result

    def handle_answer(
        self,
        session: DialogueSession,
        answer_result: AnswerResult,
    ) -> DialoguePhase:
        """Handle a captured answer and update session state.

        Args:
            session: Current dialogue session.
            answer_result: Result from answer extraction.

        Returns:
            Next dialogue phase after handling the answer.
        """
        question_number = session.get_current_question_number()
        if question_number is None:
            logger.warning(
                "handle_answer called outside Q&A phase",
                extra={"call_id": session.context.call_id},
            )
            return session.state.phase

        if answer_result.intent == UserIntent.ANSWER and answer_result.answer_text:
            # Store the answer
            question_text = session.get_question_text(question_number)
            was_repeated = session.state.repeat_counts.get(question_number, 0) > 0

            answer = QuestionAnswer(
                question_number=question_number,
                question_text=question_text,
                answer_text=answer_result.answer_text,
                confidence=answer_result.confidence,
                was_repeated=was_repeated,
            )
            session.state.answers[question_number] = answer
            session.state.question_states[question_number] = QuestionState.ANSWERED
            session.update_timestamp()

            logger.info(
                f"Answer captured for Q{question_number}",
                extra={
                    "call_id": session.context.call_id,
                    "confidence": answer_result.confidence,
                    "was_repeated": was_repeated,
                },
            )

            # Transition to next phase
            return self._get_next_phase_after_answer(session, question_number)

        elif answer_result.intent == UserIntent.REPEAT_REQUEST:
            return self._handle_repeat_request(session, question_number)

        else:
            # Unclear or off-topic - stay on current question
            logger.info(
                f"Unclear response for Q{question_number}, staying on question",
                extra={
                    "call_id": session.context.call_id,
                    "intent": answer_result.intent.value,
                },
            )
            return session.state.phase

    def _handle_repeat_request(
        self,
        session: DialogueSession,
        question_number: int,
    ) -> DialoguePhase:
        """Handle a repeat request for the current question.

        Args:
            session: Current dialogue session.
            question_number: Current question number.

        Returns:
            Current phase (to repeat) or next phase if max repeats exceeded.
        """
        current_repeats = session.state.repeat_counts.get(question_number, 0)

        if current_repeats < self.MAX_REPEATS_PER_QUESTION:
            # Allow repeat
            session.state.repeat_counts[question_number] = current_repeats + 1
            session.state.question_states[question_number] = QuestionState.REPEAT_REQUESTED
            session.update_timestamp()

            logger.info(
                f"Repeat requested for Q{question_number}",
                extra={
                    "call_id": session.context.call_id,
                    "repeat_count": current_repeats + 1,
                },
            )
            return session.state.phase
        else:
            # Max repeats exceeded - treat as unclear and stay on question
            logger.info(
                f"Max repeats exceeded for Q{question_number}",
                extra={
                    "call_id": session.context.call_id,
                    "max_repeats": self.MAX_REPEATS_PER_QUESTION,
                },
            )
            return session.state.phase

    def _get_next_phase_after_answer(
        self,
        session: DialogueSession,
        answered_question: int,
    ) -> DialoguePhase:
        """Determine the next phase after answering a question.

        Args:
            session: Current dialogue session.
            answered_question: Question number that was just answered.

        Returns:
            Next dialogue phase.
        """
        if answered_question == 1:
            session.state.phase = DialoguePhase.QUESTION_2
            session.state.question_states[2] = QuestionState.ASKED
        elif answered_question == 2:
            session.state.phase = DialoguePhase.QUESTION_3
            session.state.question_states[3] = QuestionState.ASKED
        elif answered_question == 3:
            session.state.phase = DialoguePhase.COMPLETION

        session.update_timestamp()
        return session.state.phase

    def start_qa_flow(self, session: DialogueSession) -> DialoguePhase:
        """Start the Q&A flow after consent is granted.

        Args:
            session: Current dialogue session.

        Returns:
            First question phase.
        """
        session.state.phase = DialoguePhase.QUESTION_1
        session.state.question_states[1] = QuestionState.ASKED
        session.update_timestamp()

        logger.info(
            "Q&A flow started",
            extra={"call_id": session.context.call_id},
        )

        return DialoguePhase.QUESTION_1

    def should_repeat_question(self, session: DialogueSession) -> bool:
        """Check if the current question should be repeated.

        Args:
            session: Current dialogue session.

        Returns:
            True if question should be repeated.
        """
        question_number = session.get_current_question_number()
        if question_number is None:
            return False

        return (
            session.state.question_states.get(question_number)
            == QuestionState.REPEAT_REQUESTED
        )

    def _build_question_delivery_prompt(
        self,
        language: str,
        question_type: str,
        is_repeat: bool,
    ) -> str:
        """Build system prompt for question delivery generation.

        Args:
            language: Target language (en/it).
            question_type: Type of question (free_text, numeric, scale).
            is_repeat: Whether this is a repeat.

        Returns:
            System prompt for LLM.
        """
        lang_instruction = "English" if language == "en" else "Italian"
        repeat_instruction = (
            "This is a repeat of the question. Acknowledge that you're repeating it politely."
            if is_repeat
            else ""
        )

        type_hints = {
            "free_text": "This is an open-ended question. Encourage a detailed response.",
            "numeric": "This question expects a number as an answer. Make that clear.",
            "scale": "This question uses a scale (typically 1-10). Remind the user of the scale.",
        }
        type_hint = type_hints.get(question_type, "")

        return f"""You are a professional survey interviewer conducting a phone survey.
Your task is to deliver the given question in a natural, conversational way.

Language: {lang_instruction}
{repeat_instruction}
{type_hint}

Guidelines:
- Be polite and professional
- Keep the delivery concise but natural
- Do not add extra questions or commentary
- Maintain the original meaning of the question
- If repeating, briefly acknowledge it before asking again

Output only the question delivery text, nothing else."""

    def _build_answer_extraction_prompt(
        self,
        language: str,
        question_type: str,
    ) -> str:
        """Build system prompt for answer extraction.

        Args:
            language: Target language (en/it).
            question_type: Type of question (free_text, numeric, scale).

        Returns:
            System prompt for LLM.
        """
        type_instructions = {
            "free_text": "Extract the main content of their response as the answer.",
            "numeric": "Extract the number from their response. If they give a range, use the midpoint.",
            "scale": "Extract the scale value (number) from their response.",
        }
        type_instruction = type_instructions.get(question_type, "Extract the answer.")

        return f"""You are analyzing a user's response to a survey question.
Your task is to determine the user's intent and extract their answer if provided.

Question type: {question_type}
{type_instruction}

Analyze the response and output in this exact format:
INTENT: [ANSWER|REPEAT_REQUEST|UNCLEAR|OFF_TOPIC]
ANSWER: [extracted answer or NONE]
CONFIDENCE: [0.0-1.0]
REASONING: [brief explanation]

Intent definitions:
- ANSWER: User provided a valid answer to the question
- REPEAT_REQUEST: User asked to repeat the question (e.g., "can you repeat that?", "what was the question?", "sorry?")
- UNCLEAR: Cannot determine what the user meant
- OFF_TOPIC: User's response is unrelated to the question

Be generous in interpreting answers - if the user attempts to answer, extract what you can."""

    def _parse_answer_extraction_response(
        self,
        llm_response: str,
        raw_user_response: str,
    ) -> AnswerResult:
        """Parse LLM response for answer extraction.

        Args:
            llm_response: Raw LLM response.
            raw_user_response: Original user response.

        Returns:
            Parsed answer result.
        """
        lines = llm_response.strip().split("\n")
        intent = UserIntent.UNCLEAR
        answer_text = None
        confidence = 0.5
        reasoning = None

        for line in lines:
            line = line.strip()
            if line.startswith("INTENT:"):
                intent_str = line.replace("INTENT:", "").strip().upper()
                try:
                    intent = UserIntent(intent_str.lower())
                except ValueError:
                    intent = UserIntent.UNCLEAR

            elif line.startswith("ANSWER:"):
                answer_str = line.replace("ANSWER:", "").strip()
                if answer_str.upper() != "NONE" and answer_str:
                    answer_text = answer_str

            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    confidence = 0.5

            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()

        return AnswerResult(
            intent=intent,
            answer_text=answer_text,
            confidence=confidence,
            raw_response=raw_user_response,
            reasoning=reasoning,
        )

    async def generate_acknowledgment(
        self,
        session: DialogueSession,
        answer: QuestionAnswer,
    ) -> str:
        """Generate a brief acknowledgment after capturing an answer.

        Args:
            session: Current dialogue session.
            answer: Captured answer.

        Returns:
            Acknowledgment text.
        """
        language = session.context.language
        lang_instruction = "English" if language == "en" else "Italian"

        system_prompt = f"""You are a professional survey interviewer.
Generate a very brief acknowledgment (1 short sentence) after receiving an answer.
Language: {lang_instruction}

Guidelines:
- Be brief and natural
- Do not repeat the answer back
- Do not add commentary on the answer
- Just acknowledge receipt and prepare to move on

Output only the acknowledgment text."""

        messages = [
            {
                "role": "user",
                "content": f"User answered: {answer.answer_text}",
            }
        ]

        try:
            acknowledgment = await self._llm_gateway.chat_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=50,
            )
            return acknowledgment.strip()
        except Exception as e:
            logger.error(
                f"LLM error generating acknowledgment: {e}",
                extra={"call_id": session.context.call_id},
            )
            # Fallback acknowledgments
            if language == "it":
                return "Grazie."
            return "Thank you."

    async def generate_completion_message(
        self,
        session: DialogueSession,
    ) -> str:
        """Generate the survey completion message.

        Args:
            session: Current dialogue session.

        Returns:
            Completion message text.
        """
        language = session.context.language
        lang_instruction = "English" if language == "en" else "Italian"

        system_prompt = f"""You are a professional survey interviewer.
Generate a brief closing message to thank the participant for completing the survey.
Language: {lang_instruction}

Guidelines:
- Thank them for their time and participation
- Keep it brief (2-3 sentences max)
- Be warm but professional
- Say goodbye

Output only the closing message."""

        messages = [
            {
                "role": "user",
                "content": "Generate survey completion message.",
            }
        ]

        try:
            completion_msg = await self._llm_gateway.chat_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=100,
            )
            return completion_msg.strip()
        except Exception as e:
            logger.error(
                f"LLM error generating completion message: {e}",
                extra={"call_id": session.context.call_id},
            )
            # Fallback completion messages
            if language == "it":
                return "Grazie mille per aver completato il nostro sondaggio. La sua opinione è molto importante per noi. Arrivederci!"
            return "Thank you so much for completing our survey. Your feedback is very valuable to us. Goodbye!"