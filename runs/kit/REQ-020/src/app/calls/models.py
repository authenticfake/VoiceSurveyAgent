"""
Call detail models for REQ-020.

Defines response schemas for call detail API.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CallAttemptOutcome(str, Enum):
    """Possible outcomes for a call attempt."""
    COMPLETED = "completed"
    REFUSED = "refused"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"


class TranscriptSnippet(BaseModel):
    """Transcript snippet for a call."""
    text: str = Field(..., description="Transcript text content")
    language: str = Field(..., description="Language code (en/it)")
    created_at: datetime = Field(..., description="When transcript was created")


class CallDetailResponse(BaseModel):
    """Response model for call detail API."""
    call_id: str = Field(..., description="Internal call identifier")
    contact_id: UUID = Field(..., description="Associated contact ID")
    campaign_id: UUID = Field(..., description="Associated campaign ID")
    attempt_number: int = Field(..., ge=1, description="Attempt number for this contact")
    provider_call_id: Optional[str] = Field(None, description="Provider's call identifier")
    outcome: CallAttemptOutcome = Field(..., description="Call outcome")
    started_at: datetime = Field(..., description="When call was initiated")
    answered_at: Optional[datetime] = Field(None, description="When call was answered")
    ended_at: Optional[datetime] = Field(None, description="When call ended")
    error_code: Optional[str] = Field(None, description="Error code if call failed")
    provider_raw_status: Optional[str] = Field(None, description="Raw status from provider")
    transcript_snippet: Optional[TranscriptSnippet] = Field(
        None, description="Transcript snippet if available"
    )
    recording_url: Optional[str] = Field(
        None, description="Recording URL if available and not expired"
    )

    class Config:
        """Pydantic config."""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "call_id": "call-abc123",
                "contact_id": "d4444444-4444-4444-4444-444444444444",
                "campaign_id": "c2222222-2222-2222-2222-222222222222",
                "attempt_number": 1,
                "provider_call_id": "CA1234567890abcdef",
                "outcome": "completed",
                "started_at": "2024-01-15T10:30:00Z",
                "answered_at": "2024-01-15T10:30:15Z",
                "ended_at": "2024-01-15T10:35:00Z",
                "error_code": None,
                "provider_raw_status": "completed",
                "transcript_snippet": {
                    "text": "Hello, this is a survey call...",
                    "language": "en",
                    "created_at": "2024-01-15T10:35:01Z"
                },
                "recording_url": None
            }
        }