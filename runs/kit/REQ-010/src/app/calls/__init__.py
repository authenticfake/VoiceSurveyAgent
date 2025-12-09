"""
Call management module.

REQ-008: Call scheduler service
REQ-010: Telephony webhook handler (CallAttempt model)
"""

from app.calls.models import CallAttempt, CallOutcome

__all__ = [
    "CallAttempt",
    "CallOutcome",
]