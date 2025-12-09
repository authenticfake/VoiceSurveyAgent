"""
Telephony provider adapters.

REQ-009: Telephony provider adapter interface
REQ-010: Telephony webhook handler
"""

from app.telephony.adapters.twilio import TwilioAdapter

__all__ = [
    "TwilioAdapter",
]