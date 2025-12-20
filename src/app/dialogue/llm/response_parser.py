"""
Response parser for extracting control signals from LLM responses.

REQ-011: LLM gateway integration
"""

import re
from typing import NamedTuple

from app.dialogue.llm.models import ControlSignal

class ParsedResponse(NamedTuple):
    """Parsed LLM response with content and signals."""

    content: str
    signals: list[ControlSignal]
    captured_answer: str | None

# Signal patterns to detect in responses
SIGNAL_PATTERN = re.compile(r"^SIGNAL:\s*(\w+)(?::(.+))?$", re.MULTILINE)

# Map of signal strings to ControlSignal enum
SIGNAL_MAP = {
    "CONSENT_ACCEPTED": ControlSignal.CONSENT_ACCEPTED,
    "CONSENT_REFUSED": ControlSignal.CONSENT_REFUSED,
    "MOVE_TO_NEXT_QUESTION": ControlSignal.MOVE_TO_NEXT_QUESTION,
    "REPEAT_QUESTION": ControlSignal.REPEAT_QUESTION,
    "ANSWER_CAPTURED": ControlSignal.ANSWER_CAPTURED,
    "SURVEY_COMPLETE": ControlSignal.SURVEY_COMPLETE,
    "UNCLEAR_RESPONSE": ControlSignal.UNCLEAR_RESPONSE,
}

def parse_llm_response(raw_response: str) -> ParsedResponse:
    """Parse LLM response to extract content and control signals.

    Args:
        raw_response: Raw response text from LLM.

    Returns:
        ParsedResponse with cleaned content and extracted signals.
    """
    signals: list[ControlSignal] = []
    captured_answer: str | None = None

    # Find all signal lines
    matches = SIGNAL_PATTERN.findall(raw_response)

    for signal_name, signal_value in matches:
        signal_name = signal_name.strip().upper()
        if signal_name in SIGNAL_MAP:
            signals.append(SIGNAL_MAP[signal_name])

            # Extract captured answer if present
            if signal_name == "ANSWER_CAPTURED" and signal_value:
                captured_answer = signal_value.strip()

    # Remove signal lines from content
    content = SIGNAL_PATTERN.sub("", raw_response).strip()

    # If no explicit signals found, try to infer from content
    if not signals:
        signals = _infer_signals_from_content(content)

    return ParsedResponse(
        content=content,
        signals=signals,
        captured_answer=captured_answer,
    )

def _infer_signals_from_content(content: str) -> list[ControlSignal]:
    """Infer control signals from response content when not explicitly provided.

    Args:
        content: Response content text.

    Returns:
        List of inferred control signals.
    """
    signals: list[ControlSignal] = []
    content_lower = content.lower()

    # Check for consent-related patterns
    consent_positive = [
        "thank you for agreeing",
        "great, let's begin",
        "wonderful, i'll start",
        "perfect, here's the first",
    ]
    consent_negative = [
        "thank you for your time",
        "i understand",
        "no problem",
        "have a good day",
    ]

    for pattern in consent_positive:
        if pattern in content_lower:
            signals.append(ControlSignal.CONSENT_ACCEPTED)
            break

    for pattern in consent_negative:
        if pattern in content_lower and "first question" not in content_lower:
            signals.append(ControlSignal.CONSENT_REFUSED)
            break

    # Check for repeat request acknowledgment
    if "let me repeat" in content_lower or "i'll ask again" in content_lower:
        signals.append(ControlSignal.REPEAT_QUESTION)

    # Check for survey completion
    if "thank you for completing" in content_lower or "survey is complete" in content_lower:
        signals.append(ControlSignal.SURVEY_COMPLETE)

    return signals