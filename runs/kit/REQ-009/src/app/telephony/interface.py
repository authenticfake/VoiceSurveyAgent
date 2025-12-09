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
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    FAILED = "failed"
    CANCELED = "canceled"


class WebhookEventType(str, Enum):
    """Webhook event types from telephony provider."""

    CALL_INITIATED = "call.initiated"
    CALL_RINGING = "call.ringing"
    CALL_ANSWERED = "call.answered"
    CALL_COMPLETED = "call.completed"
    CALL_FAILED = "call.failed"
    CALL_NO_ANSWER = "call.no_answer"
    CALL_BUSY = "call.busy"


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
    """Parsed webhook event from telephony provider.

    Attributes:
        event_type: Type of webhook event.
        provider_call_id: Provider's call identifier.
        call_id: Internal call identifier (from metadata).
        campaign_id: Campaign UUID (from metadata).
        contact_id: Contact UUID (from metadata).
        status: Current call status.
        timestamp: Event timestamp.
        duration_seconds: Call duration (for completed calls).
        error_code: Error code (for failed calls).
        error_message: Error message (for failed calls).
        raw_payload: Original webhook payload.
    """

    event_type: WebhookEventType
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


class TelephonyProviderError(Exception):
    """Base exception for telephony provider errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        provider_response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize telephony provider error.

        Args:
            message: Error message.
            error_code: Provider-specific error code.
            provider_response: Raw provider response.
        """
        super().__init__(message)
        self.error_code = error_code
        self.provider_response = provider_response or {}


class CallInitiationError(TelephonyProviderError):
    """Error during call initiation."""

    pass


class WebhookParseError(TelephonyProviderError):
    """Error parsing webhook event."""

    pass


class TelephonyProvider(ABC):
    """Abstract interface for telephony providers.

    This interface defines the contract for telephony provider adapters.
    Implementations must provide methods for initiating calls and parsing
    webhook events.
    """

    @abstractmethod
    async def initiate_call(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Initiate an outbound call.

        Args:
            request: Call initiation request with destination and metadata.

        Returns:
            Response containing provider call ID and initial status.

        Raises:
            CallInitiationError: If call initiation fails.
        """
        ...

    @abstractmethod
    def parse_webhook_event(
        self,
        payload: dict[str, Any],
    ) -> WebhookEvent:
        """Parse a webhook event from the provider.

        Args:
            payload: Raw webhook payload from provider.

        Returns:
            Parsed webhook event with normalized fields.

        Raises:
            WebhookParseError: If payload cannot be parsed.
        """
        ...

    @abstractmethod
    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        url: str,
    ) -> bool:
        """Validate webhook signature for authenticity.

        Args:
            payload: Raw request body bytes.
            signature: Signature header value from provider.
            url: Full URL that received the webhook.

        Returns:
            True if signature is valid, False otherwise.
        """
        ...