"""
Dialogue session models and state management.

REQ-012: Dialogue orchestrator consent flow
REQ-013: Dialogue orchestrator Q&A flow
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID


class DialoguePhase(str, Enum):
    """Current phase of the dialogue."""

    INTRO = "intro"
    CONSENT = "consent"
    QUESTION_1 = "question_1"
    QUESTION_2 = "question_2"
    QUESTION_3 = "question_3"
    COMPLETION = "completion"
    TERMINATED = "terminated"


class ConsentState(str, Enum):
    """State of consent in the dialogue."""

    PENDING = "pending"
    GRANTED = "granted"
    REFUSED = "refused"


class QuestionState(str, Enum):
    """State of a question in the Q&A flow."""

    NOT_ASKED = "not_asked"
    ASKED = "asked"
    REPEAT_REQUESTED = "repeat_requested"
    ANSWERED = "answered"


@dataclass
class QuestionAnswer:
    """Captured answer for a question."""

    question_number: int
    question_text: str
    answer_text: str
    confidence: float
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    was_repeated: bool = False


@dataclass
class CallContext:
    """Context for the current call."""

    call_id: str
    campaign_id: UUID
    contact_id: UUID
    language: str
    intro_script: str
    questions: list[tuple[str, str]]  # List of (question_text, question_type)
    correlation_id: str | None = None


@dataclass
class DialogueSessionState:
    """Persistent state of a dialogue session."""

    phase: DialoguePhase = DialoguePhase.INTRO
    consent_state: ConsentState = ConsentState.PENDING
    question_states: dict[int, QuestionState] = field(
        default_factory=lambda: {1: QuestionState.NOT_ASKED, 2: QuestionState.NOT_ASKED, 3: QuestionState.NOT_ASKED}
    )
    answers: dict[int, QuestionAnswer] = field(default_factory=dict)
    repeat_counts: dict[int, int] = field(default_factory=lambda: {1: 0, 2: 0, 3: 0})
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DialogueSession:
    """Complete dialogue session with context and state."""

    context: CallContext
    state: DialogueSessionState = field(default_factory=DialogueSessionState)

    def get_current_question_number(self) -> int | None:
        """Get the current question number based on phase.

        Returns:
            Question number (1-3) or None if not in Q&A phase.
        """
        phase_to_question = {
            DialoguePhase.QUESTION_1: 1,
            DialoguePhase.QUESTION_2: 2,
            DialoguePhase.QUESTION_3: 3,
        }
        return phase_to_question.get(self.state.phase)

    def get_question_text(self, question_number: int) -> str:
        """Get the question text for a given question number.

        Args:
            question_number: Question number (1-3).

        Returns:
            Question text.

        Raises:
            ValueError: If question number is invalid.
        """
        if question_number < 1 or question_number > 3:
            raise ValueError(f"Invalid question number: {question_number}")
        return self.context.questions[question_number - 1][0]

    def get_question_type(self, question_number: int) -> str:
        """Get the question type for a given question number.

        Args:
            question_number: Question number (1-3).

        Returns:
            Question type (free_text, numeric, scale).

        Raises:
            ValueError: If question number is invalid.
        """
        if question_number < 1 or question_number > 3:
            raise ValueError(f"Invalid question number: {question_number}")
        return self.context.questions[question_number - 1][1]

    def all_questions_answered(self) -> bool:
        """Check if all 3 questions have been answered.

        Returns:
            True if all questions are answered.
        """
        return all(
            self.state.question_states.get(i) == QuestionState.ANSWERED
            for i in range(1, 4)
        )

    def get_all_answers(self) -> list[QuestionAnswer]:
        """Get all captured answers in order.

        Returns:
            List of answers for questions 1-3.
        """
        return [self.state.answers[i] for i in range(1, 4) if i in self.state.answers]

    def update_timestamp(self) -> None:
        """Update the last_updated_at timestamp."""
        self.state.last_updated_at = datetime.now(timezone.utc)