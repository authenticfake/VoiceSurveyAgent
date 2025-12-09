"""
Call detail service for REQ-020.

Business logic for retrieving call details.
"""

from typing import Optional
from uuid import UUID

from app.calls.exceptions import CallAccessDeniedError, CallNotFoundError
from app.calls.models import CallAttemptOutcome, CallDetailResponse, TranscriptSnippet
from app.calls.repository import CallRepository


class CallDetailService:
    """Service for retrieving call details."""
    
    def __init__(self, repository: CallRepository):
        """Initialize with repository.
        
        Args:
            repository: Call data repository
        """
        self._repository = repository
    
    async def get_call_detail(
        self,
        call_id: str,
        user_id: UUID,
    ) -> CallDetailResponse:
        """Get detailed information about a call.
        
        Args:
            call_id: The internal call identifier
            user_id: The requesting user's ID (for access control)
        
        Returns:
            CallDetailResponse with full call information
        
        Raises:
            CallNotFoundError: If call_id doesn't exist
            CallAccessDeniedError: If user doesn't have access to the campaign
        """
        # Fetch call attempt
        call_attempt = await self._repository.get_call_attempt_by_call_id(call_id)
        if not call_attempt:
            raise CallNotFoundError(call_id)
        
        # Check campaign access
        has_access = await self._repository.check_campaign_access(
            call_attempt.campaign_id, user_id
        )
        if not has_access:
            raise CallAccessDeniedError(call_id, "User does not have access to this campaign")
        
        # Fetch transcript if available
        transcript_snippet: Optional[TranscriptSnippet] = None
        transcript_record = await self._repository.get_transcript_for_call_attempt(
            call_attempt.id
        )
        if transcript_record:
            transcript_snippet = TranscriptSnippet(
                text=transcript_record.transcript_text,
                language=transcript_record.language,
                created_at=transcript_record.created_at,
            )
        
        # Build recording URL if available (from metadata)
        recording_url: Optional[str] = None
        if call_attempt.metadata and "recording_url" in call_attempt.metadata:
            # Check if recording hasn't expired
            recording_url = call_attempt.metadata.get("recording_url")
            # In production, would check expiration from metadata
        
        return CallDetailResponse(
            call_id=call_attempt.call_id,
            contact_id=call_attempt.contact_id,
            campaign_id=call_attempt.campaign_id,
            attempt_number=call_attempt.attempt_number,
            provider_call_id=call_attempt.provider_call_id,
            outcome=CallAttemptOutcome(call_attempt.outcome),
            started_at=call_attempt.started_at,
            answered_at=call_attempt.answered_at,
            ended_at=call_attempt.ended_at,
            error_code=call_attempt.error_code,
            provider_raw_status=call_attempt.provider_raw_status,
            transcript_snippet=transcript_snippet,
            recording_url=recording_url,
        )