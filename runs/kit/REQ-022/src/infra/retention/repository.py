"""
Repository implementation for retention operations.

REQ-022: Data retention jobs

Provides database operations for:
- Querying expired recordings and transcripts
- Deleting/anonymizing contact data
- Managing GDPR deletion requests
- Saving audit records
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infra.retention.models import (
    RetentionConfig,
    RetentionResult,
    GDPRDeletionRequest,
    GDPRRequestStatus,
)
from infra.retention.interfaces import RetentionRepository

logger = logging.getLogger(__name__)


class PostgresRetentionRepository(RetentionRepository):
    """PostgreSQL implementation of retention repository."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.
        
        Args:
            session: SQLAlchemy async session
        """
        self._session = session
    
    async def get_expired_recordings(
        self,
        cutoff_date: datetime,
        limit: int = 100,
    ) -> List[dict]:
        """Get recordings older than cutoff date."""
        query = text("""
            SELECT 
                ca.id as call_attempt_id,
                ca.metadata->>'recording_path' as recording_path,
                ca.ended_at
            FROM call_attempts ca
            WHERE ca.ended_at < :cutoff_date
            AND ca.metadata->>'recording_path' IS NOT NULL
            AND ca.metadata->>'recording_deleted' IS NULL
            ORDER BY ca.ended_at ASC
            LIMIT :limit
        """)
        
        result = await self._session.execute(
            query,
            {"cutoff_date": cutoff_date, "limit": limit}
        )
        
        return [
            {
                "call_attempt_id": row.call_attempt_id,
                "recording_path": row.recording_path,
                "ended_at": row.ended_at,
            }
            for row in result.fetchall()
        ]
    
    async def get_expired_transcripts(
        self,
        cutoff_date: datetime,
        limit: int = 100,
    ) -> List[dict]:
        """Get transcripts older than cutoff date."""
        query = text("""
            SELECT 
                ts.id,
                ts.call_attempt_id,
                ts.created_at
            FROM transcript_snippets ts
            WHERE ts.created_at < :cutoff_date
            ORDER BY ts.created_at ASC
            LIMIT :limit
        """)
        
        result = await self._session.execute(
            query,
            {"cutoff_date": cutoff_date, "limit": limit}
        )
        
        return [
            {
                "id": row.id,
                "call_attempt_id": row.call_attempt_id,
                "created_at": row.created_at,
            }
            for row in result.fetchall()
        ]
    
    async def mark_recording_deleted(self, call_attempt_id: UUID) -> bool:
        """Mark a recording as deleted in the database."""
        query = text("""
            UPDATE call_attempts
            SET metadata = jsonb_set(
                COALESCE(metadata, '{}'::jsonb),
                '{recording_deleted}',
                to_jsonb(NOW()::text)
            )
            WHERE id = :call_attempt_id
        """)
        
        result = await self._session.execute(
            query,
            {"call_attempt_id": call_attempt_id}
        )
        await self._session.commit()
        
        return result.rowcount > 0
    
    async def delete_transcript(self, transcript_id: UUID) -> bool:
        """Delete a transcript record from the database."""
        query = text("""
            DELETE FROM transcript_snippets
            WHERE id = :transcript_id
        """)
        
        result = await self._session.execute(
            query,
            {"transcript_id": transcript_id}
        )
        await self._session.commit()
        
        return result.rowcount > 0
    
    async def get_retention_config(self) -> Optional[RetentionConfig]:
        """Get retention configuration from provider_configs."""
        query = text("""
            SELECT 
                recording_retention_days,
                transcript_retention_days
            FROM provider_configs
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        result = await self._session.execute(query)
        row = result.fetchone()
        
        if row is None:
            return None
        
        return RetentionConfig(
            recording_retention_days=row.recording_retention_days or 180,
            transcript_retention_days=row.transcript_retention_days or 180,
        )
    
    async def save_retention_result(self, result: RetentionResult) -> None:
        """Save retention job result for audit purposes."""
        query = text("""
            INSERT INTO audit_logs (
                id, user_id, action, resource_type, resource_id, 
                old_value, new_value, created_at
            ) VALUES (
                :id, NULL, 'retention_job', 'system', :job_id,
                NULL, :details, :created_at
            )
        """)
        
        details = {
            "status": result.status.value,
            "recordings_deleted": result.recordings_deleted,
            "recordings_failed": result.recordings_failed,
            "transcripts_deleted": result.transcripts_deleted,
            "transcripts_failed": result.transcripts_failed,
            "total_deleted": result.total_deleted,
            "total_failed": result.total_failed,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "error_message": result.error_message,
        }
        
        import json
        await self._session.execute(
            query,
            {
                "id": str(result.job_id),
                "job_id": str(result.job_id),
                "details": json.dumps(details),
                "created_at": result.started_at,
            }
        )
        await self._session.commit()
    
    async def get_contact_data(self, contact_id: UUID) -> Optional[dict]:
        """Get all data associated with a contact for GDPR deletion."""
        # Get contact info
        contact_query = text("""
            SELECT 
                c.id, c.phone_number, c.email, c.campaign_id
            FROM contacts c
            WHERE c.id = :contact_id
        """)
        
        result = await self._session.execute(
            contact_query,
            {"contact_id": contact_id}
        )
        contact = result.fetchone()
        
        if contact is None:
            return None
        
        # Get associated recordings
        recordings_query = text("""
            SELECT 
                ca.metadata->>'recording_path' as recording_path
            FROM call_attempts ca
            WHERE ca.contact_id = :contact_id
            AND ca.metadata->>'recording_path' IS NOT NULL
        """)
        
        recordings_result = await self._session.execute(
            recordings_query,
            {"contact_id": contact_id}
        )
        
        recordings = [row.recording_path for row in recordings_result.fetchall()]
        
        return {
            "id": contact.id,
            "phone_number": contact.phone_number,
            "email": contact.email,
            "campaign_id": contact.campaign_id,
            "recordings": recordings,
        }
    
    async def delete_contact_data(self, contact_id: UUID) -> int:
        """Delete or anonymize all data for a contact. Returns count of items deleted."""
        items_deleted = 0
        
        # Delete survey responses
        survey_query = text("""
            DELETE FROM survey_responses
            WHERE contact_id = :contact_id
        """)
        result = await self._session.execute(survey_query, {"contact_id": contact_id})
        items_deleted += result.rowcount
        
        # Delete events
        events_query = text("""
            DELETE FROM events
            WHERE contact_id = :contact_id
        """)
        result = await self._session.execute(events_query, {"contact_id": contact_id})
        items_deleted += result.rowcount
        
        # Delete email notifications
        email_query = text("""
            DELETE FROM email_notifications
            WHERE contact_id = :contact_id
        """)
        result = await self._session.execute(email_query, {"contact_id": contact_id})
        items_deleted += result.rowcount
        
        # Delete transcript snippets via call attempts
        transcript_query = text("""
            DELETE FROM transcript_snippets
            WHERE call_attempt_id IN (
                SELECT id FROM call_attempts WHERE contact_id = :contact_id
            )
        """)
        result = await self._session.execute(transcript_query, {"contact_id": contact_id})
        items_deleted += result.rowcount
        
        # Delete call attempts
        calls_query = text("""
            DELETE FROM call_attempts
            WHERE contact_id = :contact_id
        """)
        result = await self._session.execute(calls_query, {"contact_id": contact_id})
        items_deleted += result.rowcount
        
        # Anonymize contact (keep for referential integrity but remove PII)
        anonymize_query = text("""
            UPDATE contacts
            SET 
                phone_number = 'DELETED',
                email = NULL,
                external_contact_id = NULL,
                state = 'excluded',
                updated_at = NOW()
            WHERE id = :contact_id
        """)
        result = await self._session.execute(anonymize_query, {"contact_id": contact_id})
        items_deleted += result.rowcount
        
        await self._session.commit()
        
        return items_deleted
    
    async def save_gdpr_request(self, request: GDPRDeletionRequest) -> None:
        """Save a GDPR deletion request."""
        query = text("""
            INSERT INTO gdpr_deletion_requests (
                id, contact_id, contact_phone, contact_email,
                requested_at, deadline, status, processed_at,
                items_deleted, error_message
            ) VALUES (
                :id, :contact_id, :contact_phone, :contact_email,
                :requested_at, :deadline, :status, :processed_at,
                :items_deleted, :error_message
            )
        """)
        
        await self._session.execute(
            query,
            {
                "id": request.id,
                "contact_id": request.contact_id,
                "contact_phone": request.contact_phone,
                "contact_email": request.contact_email,
                "requested_at": request.requested_at,
                "deadline": request.deadline,
                "status": request.status.value,
                "processed_at": request.processed_at,
                "items_deleted": request.items_deleted,
                "error_message": request.error_message,
            }
        )
        await self._session.commit()
    
    async def get_pending_gdpr_requests(
        self,
        limit: int = 100,
    ) -> List[GDPRDeletionRequest]:
        """Get pending GDPR deletion requests."""
        query = text("""
            SELECT 
                id, contact_id, contact_phone, contact_email,
                requested_at, deadline, status, processed_at,
                items_deleted, error_message
            FROM gdpr_deletion_requests
            WHERE status IN ('pending', 'processing')
            ORDER BY requested_at ASC
            LIMIT :limit
        """)
        
        result = await self._session.execute(query, {"limit": limit})
        
        requests = []
        for row in result.fetchall():
            request = GDPRDeletionRequest(
                id=row.id,
                contact_id=row.contact_id,
                contact_phone=row.contact_phone,
                contact_email=row.contact_email,
                requested_at=row.requested_at,
                deadline=row.deadline,
                status=GDPRRequestStatus(row.status),
                processed_at=row.processed_at,
                items_deleted=row.items_deleted or 0,
                error_message=row.error_message,
            )
            requests.append(request)
        
        return requests
    
    async def update_gdpr_request(self, request: GDPRDeletionRequest) -> None:
        """Update a GDPR deletion request status."""
        query = text("""
            UPDATE gdpr_deletion_requests
            SET 
                status = :status,
                processed_at = :processed_at,
                items_deleted = :items_deleted,
                error_message = :error_message
            WHERE id = :id
        """)
        
        await self._session.execute(
            query,
            {
                "id": request.id,
                "status": request.status.value,
                "processed_at": request.processed_at,
                "items_deleted": request.items_deleted,
                "error_message": request.error_message,
            }
        )
        await self._session.commit()