"""
Telephony webhook handling.

REQ-010: Telephony webhook handler
"""

from app.telephony.webhooks.handler import WebhookHandler
from app.telephony.webhooks.router import router

__all__ = [
    "WebhookHandler",
    "router",
]