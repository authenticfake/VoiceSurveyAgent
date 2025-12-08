from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class QuestionPrompt:
    """Immutable representation of a survey question prompt."""

    position: int
    text: str
    answer_type: str


@dataclass(frozen=True)
class OutboundCallRequest:
    """Payload sent to the telephony provider."""

    call_id: str
    to_number: str
    from_number: str
    language: str
    callback_url: str
    intro_script: str
    questions: List[QuestionPrompt]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutboundCallResponse:
    """Structured response returned by the telephony provider."""

    provider_call_id: str
    provider_status: str
    raw_payload: Dict[str, Any] = field(default_factory=dict)