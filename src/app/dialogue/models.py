"""
Domain models for dialogue orchestration.

REQ-012: Dialogue orchestration
REQ-013: Consent / refusal flow
REQ-014: Survey response persistence (CapturedAnswer + captured_answers)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


# ============================================================
# Enums
# ============================================================

class DialoguePhase(str, Enum):
    INTRO = "intro"
    CONSENT_REQUEST = "consent_request"
    CONSENT_PROCESSING = "consent_processing"
    QUESTIONS = "questions"
    COMPLETION = "completion"
    TERMINATION = "termination"

    # REQ-013 / consent + per-question phases
    QUESTION_1 = "question_1"
    QUESTION_2 = "question_2"
    QUESTION_3 = "question_3"


class ConsentState(str, Enum):
    PENDING = "pending"
    GIVEN = "given"
    REFUSED = "refused"


class QuestionState(str, Enum):
    NOT_ASKED = "not_asked"
    ASKED = "asked"
    ANSWERED = "answered"
    SKIPPED = "skipped"


class DialogueSessionState(str, Enum):
    """Overall state of a dialogue session (Enum)."""
    ACTIVE = "active"
    COMPLETED = "completed"
    REFUSED = "refused"
    TERMINATED = "terminated"
    ERROR = "error"


# ============================================================
# Core data classes
# ============================================================

@dataclass
class CallContext:
    """Context information for a call."""
    call_id: str
    campaign_id: UUID
    contact_id: UUID
    call_attempt_id: UUID

    # Optional routing / tracing
    language: str | None = None
    correlation_id: str | None = None

    # Campaign scripts / questions
    intro_script: str | None = None

    question_1_text: str | None = None
    question_1_type: str | None = None

    question_2_text: str | None = None
    question_2_type: str | None = None

    question_3_text: str | None = None
    question_3_type: str | None = None


@dataclass
class QuestionAnswer:
    """Answer to a question (legacy/QA)."""
    question_index: int
    question_text: str
    answer_text: str
    confidence: float | None = None
    answered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================
# REQ-014: captured answer (persistence)
# ============================================================

@dataclass
class CapturedAnswer:
    """REQ-014: captured answer used by persistence."""
    question_index: int
    question_text: str
    answer_text: str
    confidence: float | None = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================
# Runtime state (RENAMED: no collision with Enum)
# ============================================================

@dataclass
class DialogueRuntimeState:
    """Persistent state of a dialogue session (dataclass)."""
    phase: DialoguePhase = DialoguePhase.INTRO
    consent_state: ConsentState = ConsentState.PENDING

    question_states: dict[int, QuestionState] = field(
        default_factory=lambda: {
            1: QuestionState.NOT_ASKED,
            2: QuestionState.NOT_ASKED,
            3: QuestionState.NOT_ASKED,
        }
    )
    answers: dict[int, QuestionAnswer] = field(default_factory=dict)
    repeat_counts: dict[int, int] = field(default_factory=lambda: {1: 0, 2: 0, 3: 0})

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    terminated_at: datetime | None = None
    error_message: str | None = None


# ============================================================
# Dialogue Session aggregate
# ============================================================

@dataclass
class DialogueSession:
    """Represents an active dialogue session.

    Tracks the state and progress of a survey call.
    """

    id: UUID = field(default_factory=uuid4)

    # Keep BOTH for backward compatibility (some modules might still use .context)
    call_context: CallContext | None = None
    context: CallContext | None = None

    # High-level phase + overall state
    phase: DialoguePhase = DialoguePhase.INTRO
    session_state: DialogueSessionState = DialogueSessionState.ACTIVE

    # Runtime state dataclass (formerly clobbered DialogueSessionState)
    state: DialogueRuntimeState = field(default_factory=DialogueRuntimeState)

    # Consent
    consent_state: ConsentState = ConsentState.PENDING

    # Legacy "answers" used by existing flows (keep as-is)
    answers: dict[str, str] = field(default_factory=dict)
    answer_confidences: dict[str, float] = field(default_factory=dict)

    # Transcript + metadata used by orchestration/llm
    transcript: list[dict[str, str]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consent_requested_at: datetime | None = None
    consent_resolved_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # REQ-014: captured answers for persistence (non-destructive addition)
    captured_answers: list[CapturedAnswer] = field(default_factory=list)

    # --------------------------------------------------------
    # REQ-014 helpers
    # --------------------------------------------------------
    def has_all_answers(self) -> bool:
        """REQ-014: persistence requires exactly 3 captured answers."""
        return len(self.captured_answers) == 3

    # --------------------------------------------------------
    # Convenience: resolve call context
    # --------------------------------------------------------
    def get_call_context(self) -> CallContext | None:
        """Prefer call_context, fallback to context."""
        return self.call_context or self.context

    def add_utterance(self, role: str, text: str | None) -> None:
        """
        Backward-compatible alias.

        Some flows (consent/orchestrator) call add_utterance(role, text).
        Newer session models may expose a different API; we normalize here.
        """
        if not text:
            return

        # Prefer the newer canonical method/field if present.
        if hasattr(self, "add_message"):
            getattr(self, "add_message")(role, text)
            return

        if hasattr(self, "append_message"):
            getattr(self, "append_message")(role, text)
            return

        if hasattr(self, "messages") and isinstance(getattr(self, "messages"), list):
            getattr(self, "messages").append({"role": role, "content": text})
            return

        if hasattr(self, "turns") and isinstance(getattr(self, "turns"), list):
            getattr(self, "turns").append({"role": role, "text": text})
            return

        # Fallback: use transcript (present in this model)
        self.transcript.append({"role": role, "text": text})
