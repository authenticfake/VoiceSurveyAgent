"""
Telephony provider interface definition.

REQ-009: Telephony provider adapter interface
- TelephonyProvider interface defines initiate_call method
- Interface defines parse_webhook_event method
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class CallStatus(str, Enum):
    """Call status values."""

    QUEUED = "queued"
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no-answer"
    CANCELED = "canceled"
    UNKNOWN = "unknown"


class WebhookEventType(str, Enum):
    """Webhook event types from telephony provider."""

    CALL_INITIATED = "call.initiated"
    CALL_RINGING = "call.ringing"
    CALL_ANSWERED = "call.answered"
    CALL_COMPLETED = "call.completed"
    CALL_FAILED = "call.failed"
    CALL_BUSY = "call.busy"
    CALL_NO_ANSWER = "call.no-answer"


@dataclass(frozen=True)
class CallInitiationRequest:
    """Request to initiate an outbound call.

    Attributes:
        to: Destination phone number in E.164 format.
        from_number: Caller ID phone number in E.164 format.
        callback_url: URL for webhook callbacks.
        call_id: Internal call identifier for correlation.
        campaign_id: Campaign UUID for context.
        contact_id: Contact UUID for context.
        language: Language code for the call (en/it).
        metadata: Additional metadata to include in callbacks.
    """

    to: str
    from_number: str
    callback_url: str
    call_id: str
    campaign_id: UUID
    contact_id: UUID
    language: str = "en"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CallInitiationResponse:
    """Response from call initiation.

    Attributes:
        provider_call_id: Provider's unique call identifier.
        status: Initial call status.
        created_at: Timestamp when call was created.
        raw_response: Raw provider response for debugging.
    """

    provider_call_id: str
    status: CallStatus
    created_at: datetime
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookEvent:
    """Parsed webhook event from telephony provider."""

    event_type: WebhookEventType
    provider: str
    provider_call_id: str
    call_id: str | None
    campaign_id: UUID | None
    contact_id: UUID | None
    status: CallStatus
    timestamp: datetime
    duration_seconds: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)



@dataclass(frozen=True)
class TelephonyProviderError(Exception):
    """Base exception for telephony provider errors."""

    message: str
    error_code: str
    provider_response: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Ensure Exception base class carries the message for str(error)
        Exception.__init__(self, self.message)

    def __str__(self) -> str:
        return self.message



@dataclass(frozen=True)
class CallInitiationError(TelephonyProviderError):
    """Raised when call initiation fails."""


@dataclass(frozen=True)
class WebhookParseError(TelephonyProviderError):
    """Raised when webhook parsing fails."""


class TelephonyProvider(ABC):
    """Abstract base class for telephony providers."""

    @abstractmethod
    def initiate_call(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Initiate an outbound call."""

    @abstractmethod
    def parse_webhook_event(
        self,
        payload: dict[str, Any],
    ) -> WebhookEvent:
        """Parse incoming webhook payload into standardized event."""

    @abstractmethod
    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        url: str | None = None,
    ) -> bool:
        """Validate webhook signature if provider supports it."""
