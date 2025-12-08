from __future__ import annotations


class DialogueProcessingError(RuntimeError):
    """Base class for dialogue processing failures."""


class CallAttemptNotFoundError(DialogueProcessingError):
    """Raised when an incoming telephony event references an unknown call attempt."""


class UnsupportedTelephonyEventError(DialogueProcessingError):
    """Raised when an event cannot be mapped to the dialogue workflow."""


class SurveyAnswerMismatchError(DialogueProcessingError):
    """Raised when the provider payload omits one of the three mandatory answers."""