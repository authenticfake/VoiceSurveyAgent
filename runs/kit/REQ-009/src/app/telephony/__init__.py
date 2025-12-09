"""
Telephony provider adapter module.

REQ-009: Telephony provider adapter interface
- TelephonyProvider interface defines initiate_call method
- Interface defines parse_webhook_event method
- Concrete adapter implements Twilio-compatible API
- Adapter configurable via ProviderConfig entity
- Adapter is injectable for testing with mock provider
"""

from app.telephony.interface import (
    CallInitiationRequest,
    CallInitiationResponse,
    CallStatus,
    TelephonyProvider,
    WebhookEvent,
    WebhookEventType,
)
from app.telephony.twilio_adapter import TwilioAdapter
from app.telephony.factory import get_telephony_provider

__all__ = [
    "CallInitiationRequest",
    "CallInitiationResponse",
    "CallStatus",
    "TelephonyProvider",
    "TwilioAdapter",
    "WebhookEvent",
    "WebhookEventType",
    "get_telephony_provider",
]