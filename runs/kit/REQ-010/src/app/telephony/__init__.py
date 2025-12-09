"""
Telephony module for provider integration and webhook handling.

REQ-009: Telephony provider adapter interface
REQ-010: Telephony webhook handler
"""

from app.telephony.events import CallEvent, CallEventType
from app.telephony.interface import TelephonyProvider
from app.telephony.webhooks.handler import WebhookHandler
from app.telephony.webhooks.router import router as webhooks_router

__all__ = [
    "CallEvent",
    "CallEventType",
    "TelephonyProvider",
    "WebhookHandler",
    "webhooks_router",
]