"""
Unit tests for GDPR deletion service.

REQ-022: Data retention jobs
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from infra.retention.gdpr import GDPRDeletionService
from infra.retention.models import (
    GDPRDeletionRequest,
    GDPRRequestStatus,
    RetentionConfig,
)
from infra.retention.audit import InMemoryAuditLogger


class MockStorageBackend:
    """Mock storage backend for testing."""
    
    def __init__(self):
        self.deleted_objects = []
    
    async def delete_object(self, key: str) -> bool:
        self.deleted_objects.append(key)
        return True
    
    async def list_objects(self, prefix: str, older_than=None):
        return []
    
    async def object_exists(self, key: str) -> bool:
        return True


class MockGDPRRepository:
    """Mock repository for GDPR testing."""
    
    def __init__(self):
        self.saved_requests = []
        self.pending_requests = []
        self.contact_data = {}
        self.deleted_contacts = []
    
    async def get_expired_recordings(self, cutoff_date, limit=100):
        return []
    
    async def get_expired_transcripts(self, cutoff_date, limit=100):
        return []
    
    async def mark_recording_deleted(self, call_attempt_id):
        return True
    
    async def delete_transcript(self, transcript_id):
        return True
    
    async def get_retention_config(self):
        return RetentionConfig()
    
    async def save_retention_result(self, result):
        pass
    
    async def get_contact_data(self, contact_id):
        return self.contact_data.get(contact_id)
    
    async def delete_contact_data(self, contact_id):
        self.deleted_contacts.append(contact_id)
        return 10  # Simulated items deleted
    
    async def save_gdpr_request(self, request):
        self.saved_requests.append(request)
    
    async def get_pending_gdpr_requests(self, limit=100):
        return self.pending_requests[:limit]
    
    async def update_gdpr_request(self, request):
        # Update in pending list
        for i, r in enumerate(self.pending_requests):
            if r.id == request.id:
                self.pending_requests[i] = request
                break


class TestGDPRDeletionService:
    """Tests for GDPRDeletionService."""
    
    @pytest.fixture
    def mock_repository(self):
        return MockGDPRRepository()
    
    @pytest.fixture
    def mock_storage(self):
        return MockStorageBackend()
    
    @pytest.fixture
    def mock_audit_logger(self):
        return InMemoryAuditLogger()
    
    @pytest.fixture
    def service(self, mock_repository, mock_storage, mock_audit_logger):
        return GDPRDeletionService(
            repository=mock_repository,
            storage=mock_storage,
            audit_logger=mock_audit_logger,
        )
    
    @pytest.mark.asyncio
    async def test_create_deletion_request(self, service, mock_repository):
        """Test creating a GDPR deletion request."""
        contact_id = uuid4()
        
        request = await service.create_deletion_request(
            contact_id=contact_id,
            contact_phone="+14155551234",
            contact_email="test@example.com",
        )
        
        assert request.contact_id == contact_id
        assert request.status == GDPRRequestStatus.PENDING
        assert request.deadline is not None
        assert len(mock_repository.saved_requests) == 1
    
    @pytest.mark.asyncio
    async def test_create_deletion_request_sets_72h_deadline(self, service):
        """Test that deadline is set to 72 hours from request."""
        contact_id = uuid4()
        
        request = await service.create_deletion_request(contact_id=contact_id)
        
        expected_deadline = request.requested_at + timedelta(hours=72)
        assert request.deadline == expected_deadline
    
    @pytest.mark.asyncio
    async def test_process_pending_requests_empty(self, service):
        """Test processing with no pending requests."""
        processed = await service.process_pending_requests()
        
        assert len(processed) == 0
    
    @pytest.mark.asyncio
    async def test_process_pending_requests_with_contact(
        self, service, mock_repository, mock_storage
    ):
        """Test processing request with existing contact."""
        contact_id = uuid4()
        request = GDPRDeletionRequest(
            contact_id=contact_id,
            contact_phone="+14155551234",
        )
        mock_repository.pending_requests = [request]
        mock_repository.contact_data[contact_id] = {
            "id": contact_id,
            "phone_number": "+14155551234",
            "email": "test@example.com",
            "recordings": ["recordings/call1.wav", "recordings/call2.wav"],
        }
        
        processed = await service.process_pending_requests()
        
        assert len(processed) == 1
        assert processed[0].status == GDPRRequestStatus.COMPLETED
        assert processed[0].items_deleted == 10
        assert len(mock_storage.deleted_objects) == 2
    
    @pytest.mark.asyncio
    async def test_process_pending_requests_contact_not_found(
        self, service, mock_repository
    ):
        """Test processing request when contact not found."""
        contact_id = uuid4()
        request = GDPRDeletionRequest(contact_id=contact_id)
        mock_repository.pending_requests = [request]
        # contact_data is empty, so contact won't be found
        
        processed = await service.process_pending_requests()
        
        assert len(processed) == 1
        assert processed[0].status == GDPRRequestStatus.COMPLETED
        assert processed[0].items_deleted == 0
    
    @pytest.mark.asyncio
    async def test_get_overdue_requests(self, service, mock_repository):
        """Test getting overdue requests."""
        now = datetime.utcnow()
        
        overdue = GDPRDeletionRequest(
            contact_id=uuid4(),
            deadline=now - timedelta(hours=1),
        )
        not_overdue = GDPRDeletionRequest(
            contact_id=uuid4(),
            deadline=now + timedelta(hours=1),
        )
        mock_repository.pending_requests = [overdue, not_overdue]
        
        result = await service.get_overdue_requests(now)
        
        assert len(result) == 1
        assert result[0].id == overdue.id
    
    @pytest.mark.asyncio
    async def test_process_logs_to_audit(
        self, service, mock_repository, mock_audit_logger
    ):
        """Test that processing creates audit logs."""
        contact_id = uuid4()
        request = GDPRDeletionRequest(contact_id=contact_id)
        mock_repository.pending_requests = [request]
        
        await service.process_pending_requests()
        
        gdpr_logs = [l for l in mock_audit_logger.logs if l["type"] == "gdpr_request"]
        assert len(gdpr_logs) >= 2  # processing + completed