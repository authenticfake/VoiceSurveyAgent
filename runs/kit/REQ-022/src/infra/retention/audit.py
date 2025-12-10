"""
Audit logging implementation.

REQ-022: Data retention jobs

Provides audit logging for:
- Deletion operations
- Retention job executions
- GDPR request processing
"""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infra.retention.models import RetentionResult, GDPRDeletionRequest
from infra.retention.interfaces import AuditLogger

logger = logging.getLogger(__name__)


class PostgresAuditLogger:
    """PostgreSQL-based audit logger."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the audit logger.
        
        Args:
            session: SQLAlchemy async session
        """
        self._session = session
    
    async def log_deletion(
        self,
        deletion_type: str,
        resource_id: str,
        user_id: Optional[UUID],
        details: Optional[dict] = None,
    ) -> None:
        """Log a deletion event for audit purposes."""
        query = text("""
            INSERT INTO audit_logs (
                id, user_id, action, resource_type, resource_id,
                old_value, new_value, created_at
            ) VALUES (
                :id, :user_id, :action, :resource_type, :resource_id,
                NULL, :details, :created_at
            )
        """)
        
        await self._session.execute(
            query,
            {
                "id": str(uuid4()),
                "user_id": str(user_id) if user_id else None,
                "action": "delete",
                "resource_type": deletion_type,
                "resource_id": resource_id,
                "details": json.dumps(details) if details else None,
                "created_at": datetime.utcnow(),
            }
        )
        await self._session.commit()
        
        logger.debug(
            "Audit log created for deletion",
            extra={
                "deletion_type": deletion_type,
                "resource_id": resource_id,
                "user_id": str(user_id) if user_id else None,
            }
        )
    
    async def log_retention_job(self, result: RetentionResult) -> None:
        """Log retention job execution."""
        query = text("""
            INSERT INTO audit_logs (
                id, user_id, action, resource_type, resource_id,
                old_value, new_value, created_at
            ) VALUES (
                :id, NULL, :action, :resource_type, :resource_id,
                NULL, :details, :created_at
            )
        """)
        
        details = {
            "job_id": str(result.job_id),
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
        
        await self._session.execute(
            query,
            {
                "id": str(uuid4()),
                "action": "retention_job",
                "resource_type": "system",
                "resource_id": str(result.job_id),
                "details": json.dumps(details),
                "created_at": result.started_at,
            }
        )
        await self._session.commit()
        
        logger.info(
            "Retention job audit log created",
            extra={
                "job_id": str(result.job_id),
                "status": result.status.value,
                "total_deleted": result.total_deleted,
            }
        )
    
    async def log_gdpr_request(
        self,
        request: GDPRDeletionRequest,
        action: str,
    ) -> None:
        """Log GDPR request processing."""
        query = text("""
            INSERT INTO audit_logs (
                id, user_id, action, resource_type, resource_id,
                old_value, new_value, created_at
            ) VALUES (
                :id, NULL, :action, :resource_type, :resource_id,
                NULL, :details, :created_at
            )
        """)
        
        details = {
            "request_id": str(request.id),
            "contact_id": str(request.contact_id),
            "status": request.status.value,
            "requested_at": request.requested_at.isoformat(),
            "deadline": request.deadline.isoformat() if request.deadline else None,
            "processed_at": request.processed_at.isoformat() if request.processed_at else None,
            "items_deleted": request.items_deleted,
            "error_message": request.error_message,
        }
        
        await self._session.execute(
            query,
            {
                "id": str(uuid4()),
                "action": f"gdpr_{action}",
                "resource_type": "gdpr_request",
                "resource_id": str(request.id),
                "details": json.dumps(details),
                "created_at": datetime.utcnow(),
            }
        )
        await self._session.commit()
        
        logger.info(
            "GDPR request audit log created",
            extra={
                "request_id": str(request.id),
                "action": action,
                "status": request.status.value,
            }
        )


class InMemoryAuditLogger:
    """In-memory audit logger for testing."""
    
    def __init__(self):
        self.logs: list = []
    
    async def log_deletion(
        self,
        deletion_type: str,
        resource_id: str,
        user_id: Optional[UUID],
        details: Optional[dict] = None,
    ) -> None:
        """Log a deletion event."""
        self.logs.append({
            "type": "deletion",
            "deletion_type": deletion_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "details": details,
            "timestamp": datetime.utcnow(),
        })
    
    async def log_retention_job(self, result: RetentionResult) -> None:
        """Log retention job execution."""
        self.logs.append({
            "type": "retention_job",
            "result": result,
            "timestamp": datetime.utcnow(),
        })
    
    async def log_gdpr_request(
        self,
        request: GDPRDeletionRequest,
        action: str,
    ) -> None:
        """Log GDPR request processing."""
        self.logs.append({
            "type": "gdpr_request",
            "request": request,
            "action": action,
            "timestamp": datetime.utcnow(),
        })