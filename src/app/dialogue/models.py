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
class DialogueSession:
    """Represents an active dialogue session.

    Tracks the state and progress of a survey call.
    """

    id: UUID = field(default_factory=uuid4)
    call_context: CallContext | None = None
    phase: DialoguePhase = DialoguePhase.INTRO
    state: DialogueSessionState = DialogueSessionState.ACTIVE
    consent_state: ConsentState = ConsentState.PENDING
    answers: dict[str, str] = field(default_factory=dict)
    answer_confidences: dict[str, float] = field(default_factory=dict)
    transcript: list[dict[str, str]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consent_requested_at: datetime | None = None
    consent_resolved_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

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