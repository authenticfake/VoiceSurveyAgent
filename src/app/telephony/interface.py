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

import anyio


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
    """Request to initiate an outbound call."""

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
    """Response from call initiation."""

    provider_call_id: str
    status: CallStatus
    created_at: datetime
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookEvent:
    """Parsed webhook event from telephony provider."""

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
        super().__init__(message)
        self.error_code = error_code
        self.provider_response = provider_response or {}


class CallInitiationError(TelephonyProviderError):
    """Error during call initiation."""


class WebhookParseError(TelephonyProviderError):
    """Error parsing webhook event."""


class TelephonyProvider(ABC):
    """Abstract interface for telephony providers.

    Design choice for REQ-009:
    - Keep `initiate_call` async for backward compatibility.
    - Add `initiate_call_sync` as the source-of-truth for deterministic tests.
    """

    async def initiate_call(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Initiate an outbound call (async, backward compatible).

        Default implementation delegates to the sync method in a worker thread.
        """
        return await anyio.to_thread.run_sync(self.initiate_call_sync, request)

    def initiate_call_sync(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        raise NotImplementedError("sync only used in tests")


    @abstractmethod
    def parse_webhook_event(
        self,
        payload: dict[str, Any],
    ) -> WebhookEvent:
        """Parse a webhook event from the provider."""
        ...

    @abstractmethod
    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        url: str,
    ) -> bool:
        """Validate webhook signature for authenticity."""
        ...

CallInfo = CallInitiationResponse

