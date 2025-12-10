"""
Unit tests for retention models.

REQ-022: Data retention jobs
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from infra.retention.models import (
    RetentionConfig,
    DeletionRecord,
    DeletionType,
    DeletionStatus,
    RetentionResult,
    GDPRDeletionRequest,
    GDPRRequestStatus,
)


class TestRetentionConfig:
    """Tests for RetentionConfig."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = RetentionConfig()
        
        assert config.recording_retention_days == 180
        assert config.transcript_retention_days == 180
        assert config.gdpr_processing_deadline_hours == 72
        assert config.batch_size == 100
        assert config.max_retries == 3
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetentionConfig(
            recording_retention_days=90,
            transcript_retention_days=60,
            gdpr_processing_deadline_hours=48,
            batch_size=50,
            max_retries=5,
        )
        
        assert config.recording_retention_days == 90
        assert config.transcript_retention_days == 60
        assert config.gdpr_processing_deadline_hours == 48
        assert config.batch_size == 50
        assert config.max_retries == 5
    
    def test_get_recording_cutoff(self):
        """Test recording cutoff date calculation."""
        config = RetentionConfig(recording_retention_days=30)
        now = datetime(2024, 6, 15, 12, 0, 0)
        
        cutoff = config.get_recording_cutoff(now)
        
        expected = datetime(2024, 5, 16, 12, 0, 0)
        assert cutoff == expected
    
    def test_get_transcript_cutoff(self):
        """Test transcript cutoff date calculation."""
        config = RetentionConfig(transcript_retention_days=60)
        now = datetime(2024, 6, 15, 12, 0, 0)
        
        cutoff = config.get_transcript_cutoff(now)
        
        expected = datetime(2024, 4, 16, 12, 0, 0)
        assert cutoff == expected
    
    def test_get_gdpr_deadline(self):
        """Test GDPR deadline calculation."""
        config = RetentionConfig(gdpr_processing_deadline_hours=72)
        request_time = datetime(2024, 6, 15, 12, 0, 0)
        
        deadline = config.get_gdpr_deadline(request_time)
        
        expected = datetime(2024, 6, 18, 12, 0, 0)
        assert deadline == expected


class TestDeletionRecord:
    """Tests for DeletionRecord."""
    
    def test_default_values(self):
        """Test default deletion record values."""
        record = DeletionRecord()
        
        assert record.deletion_type == DeletionType.RECORDING
        assert record.resource_id == ""
        assert record.resource_path is None
        assert record.status == DeletionStatus.PENDING
        assert record.error_message is None
        assert record.completed_at is None
    
    def test_mark_completed(self):
        """Test marking record as completed."""
        record = DeletionRecord(
            deletion_type=DeletionType.TRANSCRIPT,
            resource_id="test-123",
        )
        
        record.mark_completed()
        
        assert record.status == DeletionStatus.COMPLETED
        assert record.completed_at is not None
    
    def test_mark_failed(self):
        """Test marking record as failed."""
        record = DeletionRecord(
            deletion_type=DeletionType.RECORDING,
            resource_id="test-456",
        )
        
        record.mark_failed("Connection timeout")
        
        assert record.status == DeletionStatus.FAILED
        assert record.error_message == "Connection timeout"
        assert record.completed_at is not None


class TestRetentionResult:
    """Tests for RetentionResult."""
    
    def test_default_values(self):
        """Test default result values."""
        result = RetentionResult()
        
        assert result.status == DeletionStatus.IN_PROGRESS
        assert result.recordings_deleted == 0
        assert result.recordings_failed == 0
        assert result.transcripts_deleted == 0
        assert result.transcripts_failed == 0
        assert result.total_deleted == 0
        assert result.total_failed == 0
        assert len(result.deletion_records) == 0
    
    def test_add_completed_recording_deletion(self):
        """Test adding completed recording deletion."""
        result = RetentionResult()
        record = DeletionRecord(
            deletion_type=DeletionType.RECORDING,
            resource_id="rec-123",
        )
        record.mark_completed()
        
        result.add_deletion(record)
        
        assert result.recordings_deleted == 1
        assert result.total_deleted == 1
        assert len(result.deletion_records) == 1
    
    def test_add_failed_transcript_deletion(self):
        """Test adding failed transcript deletion."""
        result = RetentionResult()
        record = DeletionRecord(
            deletion_type=DeletionType.TRANSCRIPT,
            resource_id="trans-456",
        )
        record.mark_failed("Not found")
        
        result.add_deletion(record)
        
        assert result.transcripts_failed == 1
        assert result.total_failed == 1
    
    def test_complete_success(self):
        """Test completing with success."""
        result = RetentionResult()
        record = DeletionRecord(deletion_type=DeletionType.RECORDING)
        record.mark_completed()
        result.add_deletion(record)
        
        result.complete()
        
        assert result.status == DeletionStatus.COMPLETED
        assert result.completed_at is not None
    
    def test_complete_partial(self):
        """Test completing with partial success."""
        result = RetentionResult()
        
        success = DeletionRecord(deletion_type=DeletionType.RECORDING)
        success.mark_completed()
        result.add_deletion(success)
        
        failure = DeletionRecord(deletion_type=DeletionType.RECORDING)
        failure.mark_failed("Error")
        result.add_deletion(failure)
        
        result.complete()
        
        assert result.status == DeletionStatus.PARTIAL
    
    def test_complete_with_error(self):
        """Test completing with error."""
        result = RetentionResult()
        
        result.complete(error="Fatal error occurred")
        
        assert result.status == DeletionStatus.FAILED
        assert result.error_message == "Fatal error occurred"


class TestGDPRDeletionRequest:
    """Tests for GDPRDeletionRequest."""
    
    def test_default_values(self):
        """Test default request values."""
        contact_id = uuid4()
        request = GDPRDeletionRequest(contact_id=contact_id)
        
        assert request.contact_id == contact_id
        assert request.status == GDPRRequestStatus.PENDING
        assert request.items_deleted == 0
        assert request.deadline is not None
    
    def test_deadline_auto_calculation(self):
        """Test automatic deadline calculation."""
        request = GDPRDeletionRequest(
            contact_id=uuid4(),
            requested_at=datetime(2024, 6, 15, 12, 0, 0),
        )
        
        expected_deadline = datetime(2024, 6, 18, 12, 0, 0)
        assert request.deadline == expected_deadline
    
    def test_is_overdue_false(self):
        """Test is_overdue when not overdue."""
        request = GDPRDeletionRequest(
            contact_id=uuid4(),
            deadline=datetime(2024, 6, 20, 12, 0, 0),
        )
        
        now = datetime(2024, 6, 15, 12, 0, 0)
        assert request.is_overdue(now) is False
    
    def test_is_overdue_true(self):
        """Test is_overdue when overdue."""
        request = GDPRDeletionRequest(
            contact_id=uuid4(),
            deadline=datetime(2024, 6, 10, 12, 0, 0),
        )
        
        now = datetime(2024, 6, 15, 12, 0, 0)
        assert request.is_overdue(now) is True
    
    def test_mark_processing(self):
        """Test marking request as processing."""
        request = GDPRDeletionRequest(contact_id=uuid4())
        
        request.mark_processing()
        
        assert request.status == GDPRRequestStatus.PROCESSING
    
    def test_mark_completed(self):
        """Test marking request as completed."""
        request = GDPRDeletionRequest(contact_id=uuid4())
        
        request.mark_completed(items_deleted=15)
        
        assert request.status == GDPRRequestStatus.COMPLETED
        assert request.items_deleted == 15
        assert request.processed_at is not None
    
    def test_mark_failed(self):
        """Test marking request as failed."""
        request = GDPRDeletionRequest(contact_id=uuid4())
        
        request.mark_failed("Contact not found")
        
        assert request.status == GDPRRequestStatus.FAILED
        assert request.error_message == "Contact not found"
        assert request.processed_at is not None