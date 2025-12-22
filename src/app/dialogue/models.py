"""
Domain models for dialogue orchestration.

REQ-012: Dialogue orchestrator consent flow
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

class DialoguePhase(str, Enum):
    """Phases of the dialogue flow."""

    INTRO = "intro"
    CONSENT_REQUEST = "consent_request"
    CONSENT_PROCESSING = "consent_processing"
    QUESTION_1 = "question_1"
    QUESTION_2 = "question_2"
    QUESTION_3 = "question_3"
    COMPLETION = "completion"
    REFUSED = "refused"
    TERMINATED = "terminated"

class ConsentState(str, Enum):
    """State of consent in the dialogue."""

    PENDING = "pending"
    GRANTED = "granted"
    REFUSED = "refused"
    UNCLEAR = "unclear"

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

class DialogueSessionState(str, Enum):
    """Overall state of a dialogue session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    REFUSED = "refused"
    TERMINATED = "terminated"
    
    ERROR = "error"

@dataclass
class CallContext:
    """Context information for a call.

    Contains all the information needed to conduct the survey dialogue.
    """

    call_id: str
    campaign_id: UUID
    contact_id: UUID
    call_attempt_id: UUID
    language: str  # 'en' or 'it'
    intro_script: str
    questions: list[tuple[str, str]]  # List of (question_text, question_type)
    question_1_text: str
    question_1_type: str
    question_2_text: str
    question_2_type: str
    question_3_text: str
    question_3_type: str
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        """Validate call context after initialization."""
        if self.language not in ("en", "it"):
            raise ValueError(f"Unsupported language: {self.language}")
        if not self.intro_script:
            raise ValueError("Intro script is required")
        if not all([self.question_1_text, self.question_2_text, self.question_3_text]):
            raise ValueError("All three questions are required")

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
    """Represents an active dialogue session.

    Tracks the state and progress of a survey call.
    """

    id: UUID = field(default_factory=uuid4)
    call_context: CallContext | None = None
    context: CallContext | None = None
    phase: DialoguePhase = DialoguePhase.INTRO
    state: DialogueSessionState = field(default_factory=DialogueSessionState)
    consent_state: ConsentState = ConsentState.PENDING
    answers: dict[str, str] = field(default_factory=dict)
    answer_confidences: dict[str, float] = field(default_factory=dict)
    transcript: list[dict[str, str]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consent_requested_at: datetime | None = None
    consent_resolved_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

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

    def add_utterance(self, role: str, text: str) -> None:
        """Add an utterance to the transcript.

        Args:
            role: Speaker role ('agent' or 'user').
            text: Utterance text.
        """
        self.transcript.append({
            "role": role,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def set_consent_granted(self) -> None:
        """Mark consent as granted."""
        self.consent_state = ConsentState.GRANTED
        self.consent_resolved_at = datetime.now(timezone.utc)
        self.phase = DialoguePhase.QUESTION_1

    def set_consent_refused(self) -> None:
        """Mark consent as refused."""
        self.consent_state = ConsentState.REFUSED
        self.consent_resolved_at = datetime.now(timezone.utc)
        self.phase = DialoguePhase.REFUSED
        self.state = DialogueSessionState.REFUSED

    def set_answer(self, question_num: int, answer: str, confidence: float = 1.0) -> None:
        """Record an answer for a question.

        Args:
            question_num: Question number (1, 2, or 3).
            answer: The captured answer.
            confidence: Confidence score (0-1).
        """
        key = f"q{question_num}"
        self.answers[key] = answer
        self.answer_confidences[key] = confidence

    def mark_completed(self) -> None:
        """Mark the session as completed."""
        self.state = DialogueSessionState.COMPLETED
        self.phase = DialoguePhase.COMPLETION
        self.completed_at = datetime.now(timezone.utc)

    def mark_terminated(self, reason: str | None = None) -> None:
        """Mark the session as terminated.

        Args:
            reason: Optional reason for termination.
        """
        self.state = DialogueSessionState.TERMINATED
        self.phase = DialoguePhase.TERMINATED
        self.completed_at = datetime.now(timezone.utc)
        if reason:
            self.metadata["termination_reason"] = reason