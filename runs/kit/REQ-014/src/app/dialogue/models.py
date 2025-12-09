"""
Domain models for dialogue orchestration.

REQ-012: Dialogue orchestrator consent flow
REQ-013: Dialogue orchestrator Q&A flow
REQ-014: Survey response persistence
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


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


class DialogueSessionState(str, Enum):
    """Overall state of the dialogue session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    REFUSED = "refused"
    FAILED = "failed"


@dataclass
class CallContext:
    """Context information for a call."""

    call_id: str
    campaign_id: UUID
    contact_id: UUID
    call_attempt_id: UUID
    language: str = "en"
    intro_script: str = ""
    questions: list[str] = field(default_factory=list)
    question_types: list[str] = field(default_factory=list)


@dataclass
class CapturedAnswer:
    """A captured answer from the survey."""

    question_index: int
    question_text: str
    answer_text: str
    confidence: float = 0.0
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DialogueSession:
    """Represents an active dialogue session."""

    id: UUID = field(default_factory=uuid4)
    call_context: CallContext | None = None
    phase: DialoguePhase = DialoguePhase.INTRO
    consent_state: ConsentState = ConsentState.PENDING
    state: DialogueSessionState = DialogueSessionState.ACTIVE
    answers: list[CapturedAnswer] = field(default_factory=list)
    current_question_index: int = 0
    repeat_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_answer(self, answer: CapturedAnswer) -> None:
        """Add a captured answer to the session.

        Args:
            answer: The captured answer to add.
        """
        self.answers.append(answer)
        self.updated_at = datetime.now(timezone.utc)

    def get_answer(self, question_index: int) -> CapturedAnswer | None:
        """Get answer for a specific question.

        Args:
            question_index: Index of the question (0-based).

        Returns:
            The captured answer or None if not found.
        """
        for answer in self.answers:
            if answer.question_index == question_index:
                return answer
        return None

    def has_all_answers(self) -> bool:
        """Check if all 3 answers have been captured.

        Returns:
            True if all 3 answers are captured.
        """
        return len(self.answers) >= 3

    def mark_completed(self) -> None:
        """Mark the session as completed."""
        self.state = DialogueSessionState.COMPLETED
        self.phase = DialoguePhase.COMPLETION
        self.updated_at = datetime.now(timezone.utc)

    def mark_refused(self) -> None:
        """Mark the session as refused."""
        self.state = DialogueSessionState.REFUSED
        self.consent_state = ConsentState.REFUSED
        self.phase = DialoguePhase.TERMINATED
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self) -> None:
        """Mark the session as failed."""
        self.state = DialogueSessionState.FAILED
        self.phase = DialoguePhase.TERMINATED
        self.updated_at = datetime.now(timezone.utc)