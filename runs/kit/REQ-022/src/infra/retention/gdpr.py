"""
GDPR deletion service.

REQ-022: Data retention jobs

Handles GDPR data subject deletion requests with:
- 72-hour processing deadline
- Complete data removal for contacts
- Audit trail for compliance
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from infra.retention.models import (
    GDPRDeletionRequest,
    GDPRRequestStatus,
    RetentionConfig,
)
from infra.retention.interfaces import (
    StorageBackend,
    RetentionRepository,
    AuditLogger,
)

logger = logging.getLogger(__name__)


class GDPRDeletionService:
    """
    Service for processing GDPR deletion requests.
    
    Ensures data subject requests are processed within 72 hours
    and all associated data is properly deleted or anonymized.
    """
    
    def __init__(
        self,
        repository: RetentionRepository,
        storage: StorageBackend,
        audit_logger: AuditLogger,
        config: Optional[RetentionConfig] = None,
    ):
        """
        Initialize the GDPR deletion service.
        
        Args:
            repository: Database repository for GDPR operations
            storage: Object storage backend for recordings
            audit_logger: Audit logger for compliance tracking
            config: Optional retention configuration
        """
        self._repository = repository
        self._storage = storage
        self._audit_logger = audit_logger
        self._config = config or RetentionConfig()
    
    async def create_deletion_request(
        self,
        contact_id: UUID,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        requested_by: Optional[UUID] = None,
    ) -> GDPRDeletionRequest:
        """
        Create a new GDPR deletion request.
        
        Args:
            contact_id: ID of the contact to delete
            contact_phone: Optional phone number for verification
            contact_email: Optional email for verification
            requested_by: Optional ID of user creating the request
            
        Returns:
            Created GDPRDeletionRequest
        """
        request = GDPRDeletionRequest(
            contact_id=contact_id,
            contact_phone=contact_phone,
            contact_email=contact_email,
        )
        
        await self._repository.save_gdpr_request(request)
        
        await self._audit_logger.log_gdpr_request(request, "created")
        
        logger.info(
            "GDPR deletion request created",
            extra={
                "request_id": str(request.id),
                "contact_id": str(contact_id),
                "deadline": request.deadline.isoformat() if request.deadline else None,
                "requested_by": str(requested_by) if requested_by else None,
            }
        )
        
        return request
    
    async def process_pending_requests(
        self,
        now: Optional[datetime] = None,
    ) -> List[GDPRDeletionRequest]:
        """
        Process all pending GDPR deletion requests.
        
        Args:
            now: Current time (for testing)
            
        Returns:
            List of processed requests
        """
        now = now or datetime.utcnow()
        processed: List[GDPRDeletionRequest] = []
        
        pending = await self._repository.get_pending_gdpr_requests(limit=100)
        
        logger.info(
            "Processing pending GDPR requests",
            extra={"count": len(pending)}
        )
        
        for request in pending:
            try:
                await self._process_single_request(request, now)
                processed.append(request)
            except Exception as e:
                logger.exception(
                    "Failed to process GDPR request",
                    extra={
                        "request_id": str(request.id),
                        "error": str(e),
                    }
                )
                request.mark_failed(str(e))
                await self._repository.update_gdpr_request(request)
                await self._audit_logger.log_gdpr_request(request, "failed")
                processed.append(request)
        
        return processed
    
    async def _process_single_request(
        self,
        request: GDPRDeletionRequest,
        now: datetime,
    ) -> None:
        """Process a single GDPR deletion request."""
        request.mark_processing()
        await self._repository.update_gdpr_request(request)
        await self._audit_logger.log_gdpr_request(request, "processing")
        
        # Check if overdue
        if request.is_overdue(now):
            logger.warning(
                "GDPR request is overdue",
                extra={
                    "request_id": str(request.id),
                    "deadline": request.deadline.isoformat() if request.deadline else None,
                    "now": now.isoformat(),
                }
            )
        
        # Get contact data to find associated recordings
        contact_data = await self._repository.get_contact_data(request.contact_id)
        
        if contact_data is None:
            logger.warning(
                "Contact not found for GDPR request",
                extra={"contact_id": str(request.contact_id)}
            )
            request.mark_completed(items_deleted=0)
            await self._repository.update_gdpr_request(request)
            await self._audit_logger.log_gdpr_request(request, "completed_no_data")
            return
        
        # Delete recordings from storage
        recordings = contact_data.get("recordings", [])
        for recording_path in recordings:
            if recording_path:
                try:
                    await self._storage.delete_object(recording_path)
                except Exception as e:
                    logger.warning(
                        "Failed to delete recording for GDPR request",
                        extra={
                            "request_id": str(request.id),
                            "path": recording_path,
                            "error": str(e),
                        }
                    )
        
        # Delete/anonymize database records
        items_deleted = await self._repository.delete_contact_data(request.contact_id)
        
        request.mark_completed(items_deleted=items_deleted)
        await self._repository.update_gdpr_request(request)
        await self._audit_logger.log_gdpr_request(request, "completed")
        
        logger.info(
            "GDPR deletion request completed",
            extra={
                "request_id": str(request.id),
                "contact_id": str(request.contact_id),
                "items_deleted": items_deleted,
            }
        )
    
    async def get_request_status(
        self,
        request_id: UUID,
    ) -> Optional[GDPRDeletionRequest]:
        """
        Get the status of a GDPR deletion request.
        
        Args:
            request_id: ID of the request
            
        Returns:
            GDPRDeletionRequest if found, None otherwise
        """
        pending = await self._repository.get_pending_gdpr_requests(limit=1000)
        for request in pending:
            if request.id == request_id:
                return request
        return None
    
    async def get_overdue_requests(
        self,
        now: Optional[datetime] = None,
    ) -> List[GDPRDeletionRequest]:
        """
        Get all overdue GDPR deletion requests.
        
        Args:
            now: Current time (for testing)
            
        Returns:
            List of overdue requests
        """
        now = now or datetime.utcnow()
        pending = await self._repository.get_pending_gdpr_requests(limit=1000)
        return [r for r in pending if r.is_overdue(now)]