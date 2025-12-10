"""
Interfaces for retention services.

REQ-022: Data retention jobs

Defines abstract interfaces for storage backends and repositories
to enable dependency injection and testability.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Protocol
from uuid import UUID

from infra.retention.models import (
    DeletionRecord,
    RetentionResult,
    GDPRDeletionRequest,
    RetentionConfig,
)


class StorageBackend(Protocol):
    """Protocol for object storage backends (S3, local filesystem, etc.)."""
    
    async def delete_object(self, key: str) -> bool:
        """Delete an object from storage. Returns True if successful."""
        ...
    
    async def list_objects(
        self, 
        prefix: str, 
        older_than: Optional[datetime] = None
    ) -> List[str]:
        """List objects with optional age filter."""
        ...
    
    async def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        ...


class RetentionRepository(ABC):
    """Abstract repository for retention-related database operations."""
    
    @abstractmethod
    async def get_expired_recordings(
        self, 
        cutoff_date: datetime, 
        limit: int = 100
    ) -> List[dict]:
        """Get recordings older than cutoff date."""
        pass
    
    @abstractmethod
    async def get_expired_transcripts(
        self, 
        cutoff_date: datetime, 
        limit: int = 100
    ) -> List[dict]:
        """Get transcripts older than cutoff date."""
        pass
    
    @abstractmethod
    async def mark_recording_deleted(self, call_attempt_id: UUID) -> bool:
        """Mark a recording as deleted in the database."""
        pass
    
    @abstractmethod
    async def delete_transcript(self, transcript_id: UUID) -> bool:
        """Delete a transcript record from the database."""
        pass
    
    @abstractmethod
    async def get_retention_config(self) -> Optional[RetentionConfig]:
        """Get retention configuration from provider_configs."""
        pass
    
    @abstractmethod
    async def save_retention_result(self, result: RetentionResult) -> None:
        """Save retention job result for audit purposes."""
        pass
    
    @abstractmethod
    async def get_contact_data(self, contact_id: UUID) -> Optional[dict]:
        """Get all data associated with a contact for GDPR deletion."""
        pass
    
    @abstractmethod
    async def delete_contact_data(self, contact_id: UUID) -> int:
        """Delete or anonymize all data for a contact. Returns count of items deleted."""
        pass
    
    @abstractmethod
    async def save_gdpr_request(self, request: GDPRDeletionRequest) -> None:
        """Save a GDPR deletion request."""
        pass
    
    @abstractmethod
    async def get_pending_gdpr_requests(self, limit: int = 100) -> List[GDPRDeletionRequest]:
        """Get pending GDPR deletion requests."""
        pass
    
    @abstractmethod
    async def update_gdpr_request(self, request: GDPRDeletionRequest) -> None:
        """Update a GDPR deletion request status."""
        pass


class AuditLogger(Protocol):
    """Protocol for audit logging."""
    
    async def log_deletion(
        self,
        deletion_type: str,
        resource_id: str,
        user_id: Optional[UUID],
        details: Optional[dict] = None
    ) -> None:
        """Log a deletion event for audit purposes."""
        ...
    
    async def log_retention_job(
        self,
        result: RetentionResult
    ) -> None:
        """Log retention job execution."""
        ...
    
    async def log_gdpr_request(
        self,
        request: GDPRDeletionRequest,
        action: str
    ) -> None:
        """Log GDPR request processing."""
        ...