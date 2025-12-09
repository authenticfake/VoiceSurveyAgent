"""
Pydantic schemas for webhook requests and responses.

REQ-010: Telephony webhook handler
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

class WebhookEventResponse(BaseModel):
    """Response schema for webhook event processing."""

    status: str = Field(
        ...,
        description="Processing status: 'processed' or 'duplicate'",
    )
    call_id: str = Field(
        ...,
        description="Internal call identifier",
    )
    event_type: str = Field(
        ...,
        description="Type of event processed",
    )

class TwilioWebhookPayload(BaseModel):
    """Schema for Twilio webhook payload (for documentation).

    Note: Twilio sends form-encoded data, not JSON.
    This schema is for documentation purposes.
    """

    CallSid: str = Field(..., description="Twilio call SID")
    CallStatus: str = Field(..., description="Call status")
    From: str | None = Field(None, description="Caller phone number")
    To: str | None = Field(None, description="Called phone number")
    Direction: str | None = Field(None, description="Call direction")
    CallDuration: str | None = Field(None, description="Call duration in seconds")
    ErrorCode: str | None = Field(None, description="Error code if failed")
    ErrorMessage: str | None = Field(None, description="Error message if failed")
    AnsweredBy: str | None = Field(None, description="Who answered (human/machine)")

    # Custom metadata fields (passed via callback URL)
    call_id: str | None = Field(None, description="Internal call ID")
    campaign_id: str | None = Field(None, description="Campaign UUID")
    contact_id: str | None = Field(None, description="Contact UUID")