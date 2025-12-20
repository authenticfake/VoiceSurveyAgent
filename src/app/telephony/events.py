"""
Domain event models for telephony call events.

REQ-010: Telephony webhook handler
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

class CallEventType(str, Enum):
    """Types of call events from telephony provider."""

    INITIATED = "call.initiated"
    RINGING = "call.ringing"
    ANSWERED = "call.answered"
    COMPLETED = "call.completed"
    FAILED = "call.failed"
    NO_ANSWER = "call.no_answer"
    BUSY = "call.busy"

class CallEvent(BaseModel):
    """Domain model for a telephony call event.

    Parsed from provider-specific webhook payloads into a
    normalized domain representation.
    """

    event_type: CallEventType = Field(
        ...,
        description="Type of call event",
    )
    call_id: str = Field(
        ...,
        description="Internal call identifier from metadata",
    )
    provider_call_id: str = Field(
        ...,
        description="Provider's unique call identifier",
    )
    campaign_id: UUID = Field(
        ...,
        description="Campaign UUID from call metadata",
    )
    contact_id: UUID = Field(
        ...,
        description="Contact UUID from call metadata",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp",
    )
    duration_seconds: int | None = Field(
        default=None,
        description="Call duration in seconds (for completed calls)",
    )
    error_code: str | None = Field(
        default=None,
        description="Error code if call failed",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if call failed",
    )
    raw_status: str | None = Field(
        default=None,
        description="Raw status from provider",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata",
    )

    class Config:
        """Pydantic configuration."""

        frozen = True