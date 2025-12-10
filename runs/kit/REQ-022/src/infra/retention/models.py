"""
Data models for retention jobs.

REQ-022: Data retention jobs
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4


class DeletionType(str, Enum):
    """Type of deletion operation."""
    RECORDING = "recording"
    TRANSCRIPT = "transcript"
    CONTACT = "contact"
    GDPR_REQUEST = "gdpr_request"


class DeletionStatus(str, Enum):
    """Status of a deletion operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class GDPRRequestStatus(str, Enum):
    """Status of a GDPR deletion request."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RetentionConfig:
    """Configuration for retention policies."""
    recording_retention_days: int = 180
    transcript_retention_days: int = 180
    gdpr_processing_deadline_hours: int = 72
    batch_size: int = 100
    max_retries: int = 3
    
    def get_recording_cutoff(self, now: Optional[datetime] = None) -> datetime:
        """Get the cutoff date for recording deletion."""
        now = now or datetime.utcnow()
        return now - timedelta(days=self.recording_retention_days)
    
    def get_transcript_cutoff(self, now: Optional[datetime] = None) -> datetime:
        """Get the cutoff date for transcript deletion."""
        now = now or datetime.utcnow()
        return now - timedelta(days=self.transcript_retention_days)
    
    def get_gdpr_deadline(self, request_time: datetime) -> datetime:
        """Get the deadline for processing a GDPR request."""
        return request_time + timedelta(hours=self.gdpr_processing_deadline_hours)


@dataclass
class DeletionRecord:
    """Record of a single deletion operation."""
    id: UUID = field(default_factory=uuid4)
    deletion_type: DeletionType = DeletionType.RECORDING
    resource_id: str = ""
    resource_path: Optional[str] = None
    status: DeletionStatus = DeletionStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def mark_completed(self) -> None:
        """Mark the deletion as completed."""
        self.status = DeletionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
    
    def mark_failed(self, error: str) -> None:
        """Mark the deletion as failed."""
        self.status = DeletionStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()


@dataclass
class RetentionResult:
    """Result of a retention job execution."""
    job_id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: DeletionStatus = DeletionStatus.IN_PROGRESS
    recordings_deleted: int = 0
    recordings_failed: int = 0
    transcripts_deleted: int = 0
    transcripts_failed: int = 0
    total_deleted: int = 0
    total_failed: int = 0
    deletion_records: List[DeletionRecord] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def add_deletion(self, record: DeletionRecord) -> None:
        """Add a deletion record to the result."""
        self.deletion_records.append(record)
        if record.status == DeletionStatus.COMPLETED:
            self.total_deleted += 1
            if record.deletion_type == DeletionType.RECORDING:
                self.recordings_deleted += 1
            elif record.deletion_type == DeletionType.TRANSCRIPT:
                self.transcripts_deleted += 1
        elif record.status == DeletionStatus.FAILED:
            self.total_failed += 1
            if record.deletion_type == DeletionType.RECORDING:
                self.recordings_failed += 1
            elif record.deletion_type == DeletionType.TRANSCRIPT:
                self.transcripts_failed += 1
    
    def complete(self, error: Optional[str] = None) -> None:
        """Mark the job as complete."""
        self.completed_at = datetime.utcnow()
        if error:
            self.status = DeletionStatus.FAILED
            self.error_message = error
        elif self.total_failed > 0 and self.total_deleted > 0:
            self.status = DeletionStatus.PARTIAL
        elif self.total_failed > 0:
            self.status = DeletionStatus.FAILED
        else:
            self.status = DeletionStatus.COMPLETED


@dataclass
class GDPRDeletionRequest:
    """GDPR deletion request for a contact."""
    id: UUID = field(default_factory=uuid4)
    contact_id: UUID = field(default_factory=uuid4)
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    requested_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    status: GDPRRequestStatus = GDPRRequestStatus.PENDING
    processed_at: Optional[datetime] = None
    items_deleted: int = 0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.deadline is None:
            self.deadline = self.requested_at + timedelta(hours=72)
    
    def is_overdue(self, now: Optional[datetime] = None) -> bool:
        """Check if the request is past its deadline."""
        now = now or datetime.utcnow()
        return self.deadline is not None and now > self.deadline
    
    def mark_processing(self) -> None:
        """Mark the request as being processed."""
        self.status = GDPRRequestStatus.PROCESSING
    
    def mark_completed(self, items_deleted: int) -> None:
        """Mark the request as completed."""
        self.status = GDPRRequestStatus.COMPLETED
        self.processed_at = datetime.utcnow()
        self.items_deleted = items_deleted
    
    def mark_failed(self, error: str) -> None:
        """Mark the request as failed."""
        self.status = GDPRRequestStatus.FAILED
        self.processed_at = datetime.utcnow()
        self.error_message = error