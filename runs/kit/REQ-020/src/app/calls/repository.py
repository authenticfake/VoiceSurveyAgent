"""
Call repository for REQ-020.

Provides data access for call attempts and related entities.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from app.calls.models import CallAttemptOutcome, CallDetailResponse, TranscriptSnippet


class CallAttemptRecord:
    """Internal representation of a call attempt from database."""
    
    def __init__(
        self,
        id: UUID,
        contact_id: UUID,
        campaign_id: UUID,
        attempt_number: int,
        call_id: str,
        provider_call_id: Optional[str],
        started_at: datetime,
        answered_at: Optional[datetime],
        ended_at: Optional[datetime],
        outcome: str,
        provider_raw_status: Optional[str],
        error_code: Optional[str],
        metadata: Optional[dict],
    ):
        self.id = id
        self.contact_id = contact_id
        self.campaign_id = campaign_id
        self.attempt_number = attempt_number
        self.call_id = call_id
        self.provider_call_id = provider_call_id
        self.started_at = started_at
        self.answered_at = answered_at
        self.ended_at = ended_at
        self.outcome = outcome
        self.provider_raw_status = provider_raw_status
        self.error_code = error_code
        self.metadata = metadata or {}


class TranscriptRecord:
    """Internal representation of a transcript snippet from database."""
    
    def __init__(
        self,
        id: UUID,
        call_attempt_id: UUID,
        transcript_text: str,
        language: str,
        created_at: datetime,
    ):
        self.id = id
        self.call_attempt_id = call_attempt_id
        self.transcript_text = transcript_text
        self.language = language
        self.created_at = created_at


class CallRepository(Protocol):
    """Protocol for call data access."""
    
    async def get_call_attempt_by_call_id(self, call_id: str) -> Optional[CallAttemptRecord]:
        """Retrieve a call attempt by its call_id."""
        ...
    
    async def get_transcript_for_call_attempt(self, call_attempt_id: UUID) -> Optional[TranscriptRecord]:
        """Retrieve transcript snippet for a call attempt."""
        ...
    
    async def check_campaign_access(self, campaign_id: UUID, user_id: UUID) -> bool:
        """Check if user has access to the campaign."""
        ...


class PostgresCallRepository:
    """PostgreSQL implementation of CallRepository."""
    
    def __init__(self, db_session):
        """Initialize with database session.
        
        Args:
            db_session: SQLAlchemy async session or connection pool
        """
        self._db = db_session
    
    async def get_call_attempt_by_call_id(self, call_id: str) -> Optional[CallAttemptRecord]:
        """Retrieve a call attempt by its call_id."""
        query = """
            SELECT 
                id, contact_id, campaign_id, attempt_number, call_id,
                provider_call_id, started_at, answered_at, ended_at,
                outcome, provider_raw_status, error_code, metadata
            FROM call_attempts
            WHERE call_id = $1
        """
        row = await self._db.fetchrow(query, call_id)
        if not row:
            return None
        
        return CallAttemptRecord(
            id=row["id"],
            contact_id=row["contact_id"],
            campaign_id=row["campaign_id"],
            attempt_number=row["attempt_number"],
            call_id=row["call_id"],
            provider_call_id=row["provider_call_id"],
            started_at=row["started_at"],
            answered_at=row["answered_at"],
            ended_at=row["ended_at"],
            outcome=row["outcome"],
            provider_raw_status=row["provider_raw_status"],
            error_code=row["error_code"],
            metadata=row["metadata"],
        )
    
    async def get_transcript_for_call_attempt(self, call_attempt_id: UUID) -> Optional[TranscriptRecord]:
        """Retrieve transcript snippet for a call attempt."""
        query = """
            SELECT id, call_attempt_id, transcript_text, language, created_at
            FROM transcript_snippets
            WHERE call_attempt_id = $1
        """
        row = await self._db.fetchrow(query, call_attempt_id)
        if not row:
            return None
        
        return TranscriptRecord(
            id=row["id"],
            call_attempt_id=row["call_attempt_id"],
            transcript_text=row["transcript_text"],
            language=row["language"],
            created_at=row["created_at"],
        )
    
    async def check_campaign_access(self, campaign_id: UUID, user_id: UUID) -> bool:
        """Check if user has access to the campaign.
        
        For now, all authenticated users with campaign_manager or admin role
        can access any campaign (single-tenant model).
        """
        # In single-tenant model, access is controlled by RBAC at route level
        # This method can be extended for multi-tenant scenarios
        return True