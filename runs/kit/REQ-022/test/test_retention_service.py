"""
Unit tests for retention service.

REQ-022: Data retention jobs
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from infra.retention.service import RetentionService
from infra.retention.models import (
    RetentionConfig,
    DeletionStatus,
    DeletionType,
)
from infra.retention.audit import InMemoryAuditLogger


class MockStorageBackend:
    """Mock storage backend for testing."""
    
    def __init__(self):
        self.deleted_objects = []
        self.should_fail = False
        self.fail_keys = set()
    
    async def delete_object(self, key: str) -> bool:
        if self.should_fail or key in self.fail_keys:
            raise Exception(f"Failed to delete {key}")
        self.deleted_objects.append(key)
        return True
    
    async def list_objects(self, prefix: str, older_than=None):
        return []
    
    async def object_exists(self, key: str) -> bool:
        return key not in self.deleted_objects


class MockRetentionRepository:
    """Mock repository for testing."""
    
    def __init__(self):
        self.expired_recordings = []
        self.expired_transcripts = []
        self.deleted_recordings = []
        self.deleted_transcripts = []
        self.saved_results = []
        self.config = RetentionConfig()
    
    async def get_expired_recordings(self, cutoff_date, limit=100):
        # Return recordings once, then empty to prevent infinite loop
        result = self.expired_recordings[:limit]
        self.expired_recordings = self.expired_recordings[limit:]
        return result
    
    async def get_expired_transcripts(self, cutoff_date, limit=100):
        result = self.expired_transcripts[:limit]
        self.expired_transcripts = self.expired_transcripts[limit:]
        return result
    
    async def mark_recording_deleted(self, call_attempt_id):
        self.deleted_recordings.append(call_attempt_id)
        return True
    
    async def delete_transcript(self, transcript_id):
        self.deleted_transcripts.append(transcript_id)
        return True
    
    async def get_retention_config(self):
        return self.config
    
    async def save_retention_result(self, result):
        self.saved_results.append(result)
    
    async def get_contact_data(self, contact_id):
        return None
    
    async def delete_contact_data(self, contact_id):
        return 0
    
    async def save_gdpr_request(self, request):
        pass
    
    async def get_pending_gdpr_requests(self, limit=100):
        return []
    
    async def update_gdpr_request(self, request):
        pass


class TestRetentionService:
    """Tests for RetentionService."""
    
    @pytest.fixture
    def mock_repository(self):
        return MockRetentionRepository()
    
    @pytest.fixture
    def mock_storage(self):
        return MockStorageBackend()
    
    @pytest.fixture
    def mock_audit_logger(self):
        return InMemoryAuditLogger()
    
    @pytest.fixture
    def service(self, mock_repository, mock_storage, mock_audit_logger):
        return RetentionService(
            repository=mock_repository,
            storage=mock_storage,
            audit_logger=mock_audit_logger,
        )
    
    @pytest.mark.asyncio
    async def test_run_retention_job_no_expired_data(self, service):
        """Test retention job with no expired data."""
        result = await service.run_retention_job()
        
        assert result.status == DeletionStatus.COMPLETED
        assert result.total_deleted == 0
        assert result.total_failed == 0
    
    @pytest.mark.asyncio
    async def test_run_retention_job_with_recordings(
        self, service, mock_repository, mock_storage
    ):
        """Test retention job deletes expired recordings."""
        mock_repository.expired_recordings = [
            {
                "call_attempt_id": uuid4(),
                "recording_path": "recordings/test1.wav",
                "ended_at": datetime.utcnow() - timedelta(days=200),
            },
            {
                "call_attempt_id": uuid4(),
                "recording_path": "recordings/test2.wav",
                "ended_at": datetime.utcnow() - timedelta(days=190),
            },
        ]
        
        result = await service.run_retention_job()
        
        assert result.status == DeletionStatus.COMPLETED
        assert result.recordings_deleted == 2
        assert result.total_deleted == 2
        assert len(mock_storage.deleted_objects) == 2
    
    @pytest.mark.asyncio
    async def test_run_retention_job_with_transcripts(
        self, service, mock_repository
    ):
        """Test retention job deletes expired transcripts."""
        mock_repository.expired_transcripts = [
            {
                "id": uuid4(),
                "call_attempt_id": uuid4(),
                "created_at": datetime.utcnow() - timedelta(days=200),
            },
        ]
        
        result = await service.run_retention_job()
        
        assert result.status == DeletionStatus.COMPLETED
        assert result.transcripts_deleted == 1
        assert result.total_deleted == 1
    
    @pytest.mark.asyncio
    async def test_run_retention_job_partial_failure(
        self, service, mock_repository, mock_storage
    ):
        """Test retention job handles partial failures."""
        mock_repository.expired_recordings = [
            {
                "call_attempt_id": uuid4(),
                "recording_path": "recordings/success.wav",
                "ended_at": datetime.utcnow() - timedelta(days=200),
            },
            {
                "call_attempt_id": uuid4(),
                "recording_path": "recordings/fail.wav",
                "ended_at": datetime.utcnow() - timedelta(days=200),
            },
        ]
        mock_storage.fail_keys = {"recordings/fail.wav"}
        
        result = await service.run_retention_job()
        
        assert result.status == DeletionStatus.PARTIAL
        assert result.recordings_deleted == 1
        assert result.recordings_failed == 1
    
    @pytest.mark.asyncio
    async def test_run_retention_job_dry_run(
        self, service, mock_repository, mock_storage
    ):
        """Test retention job dry run doesn't delete."""
        mock_repository.expired_recordings = [
            {
                "call_attempt_id": uuid4(),
                "recording_path": "recordings/test.wav",
                "ended_at": datetime.utcnow() - timedelta(days=200),
            },
        ]
        
        result = await service.run_retention_job(dry_run=True)
        
        assert result.status == DeletionStatus.COMPLETED
        assert result.recordings_deleted == 1
        assert len(mock_storage.deleted_objects) == 0  # Nothing actually deleted
    
    @pytest.mark.asyncio
    async def test_run_retention_job_saves_result(
        self, service, mock_repository
    ):
        """Test retention job saves result to database."""
        result = await service.run_retention_job()
        
        assert len(mock_repository.saved_results) == 1
        assert mock_repository.saved_results[0].job_id == result.job_id
    
    @pytest.mark.asyncio
    async def test_run_retention_job_logs_to_audit(
        self, service, mock_audit_logger
    ):
        """Test retention job creates audit log."""
        result = await service.run_retention_job()
        
        assert len(mock_audit_logger.logs) >= 1
        job_logs = [l for l in mock_audit_logger.logs if l["type"] == "retention_job"]
        assert len(job_logs) == 1
    
    @pytest.mark.asyncio
    async def test_trigger_manual_cleanup(
        self, service, mock_repository
    ):
        """Test manual cleanup with custom retention."""
        user_id = uuid4()
        
        result = await service.trigger_manual_cleanup(
            user_id=user_id,
            recording_retention_days=30,
        )
        
        assert result.status == DeletionStatus.COMPLETED