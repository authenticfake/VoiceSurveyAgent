from __future__ import annotations

import enum


class TelephonyEventName(str, enum.Enum):
    CALL_INITIATED = "call.initiated"
    CALL_RINGING = "call.ringing"
    CALL_ANSWERED = "call.answered"
    CALL_COMPLETED = "call.completed"
    CALL_FAILED = "call.failed"
    CALL_NO_ANSWER = "call.no_answer"
    CALL_BUSY = "call.busy"


class ConsentDecision(str, enum.Enum):
    ACCEPTED = "accepted"
    REFUSED = "refused"