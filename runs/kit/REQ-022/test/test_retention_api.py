"""
Integration tests for retention API endpoints.

REQ-022: Data retention jobs
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
from httpx import ASGITransport

from infra.retention.api import (
    router,
    configure_services,
    TriggerRetentionRequest,
)
from infra.retention.models import (
    RetentionResult,
    DeletionStatus,
    GDPRDeletionRequest,
    GDPRRequestStatus,
)


class MockRetentionService:
    """Mock retention service for API testing."""
    
    def __init__(self):
        self._config = MagicMock()
        self._config.recording_retention_days = 180
        self._config.transcript_retention_days = 180
    
    async def _get_config(self):
        return self._config
    
    async def run_retention_job(self, now=None, dry_run=False):
        result = RetentionResult()
        result.recordings_deleted = 5
        result.transcripts_deleted = 3
        result.total_deleted = 8
        result.complete()
        return result


class MockGDPRService:
    """Mock GDPR service for API testing."""
    
    def __init__(self):
        self._repository = MagicMock()
        self._repository.get_pending_gdpr_requests = AsyncMock(return_value=[])
        self.created_requests = []
    
    async def create_deletion_request(self, contact_id, contact_phone=None, contact_email=None):
        request = GDPRDeletionRequest(
            contact_id=contact_id,
            contact_phone=contact_phone,
            contact_email=contact_email,
        )
        self.created_requests.append(request)
        return request
    
    async def get_request_status(self, request_id):
        for r in self.created_requests:
            if r.id == request_id:
                return r
        return None
    
    async def process_pending_requests(self):
        return []
    
    async def get_overdue_requests(self, now=None):
        return []


class MockScheduler:
    """Mock scheduler for API testing."""
    
    def __init__(self):
        self._running = True


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    
    # Configure mock services
    configure_services(
        retention_service=MockRetentionService(),
        gdpr_service=MockGDPRService(),
        scheduler=MockScheduler(),
    )
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestRetentionAPI:
    """Tests for retention API endpoints."""
    
    def test_trigger_retention_job(self, client):
        """Test triggering retention job."""
        response = client.post(
            "/api/admin/retention/trigger",
            json={"dry_run": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["recordings_deleted"] == 5
        assert data["transcripts_deleted"] == 3
        assert data["total_deleted"] == 8
    
    def test_trigger_retention_job_dry_run(self, client):
        """Test triggering retention job with dry run."""
        response = client.post(
            "/api/admin/retention/trigger",
            json={"dry_run": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
    
    def test_trigger_retention_job_custom_retention(self, client):
        """Test triggering with custom retention days."""
        response = client.post(
            "/api/admin/retention/trigger",
            json={
                "recording_retention_days": 30,
                "transcript_retention_days": 60,
            }
        )
        
        assert response.status_code == 200
    
    def test_create_gdpr_request(self, client):
        """Test creating GDPR deletion request."""
        contact_id = str(uuid4())
        
        response = client.post(
            "/api/admin/retention/gdpr",
            json={
                "contact_id": contact_id,
                "contact_phone": "+14155551234",
                "contact_email": "test@example.com",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["contact_id"] == contact_id
        assert data["status"] == "pending"
        assert data["deadline"] is not None
    
    def test_get_gdpr_request_not_found(self, client):
        """Test getting non-existent GDPR request."""
        request_id = str(uuid4())
        
        response = client.get(f"/api/admin/retention/gdpr/{request_id}")
        
        assert response.status_code == 404
    
    def test_process_gdpr_requests(self, client):
        """Test triggering GDPR processing."""
        response = client.post("/api/admin/retention/gdpr/process")
        
        assert response.status_code == 200
        data = response.json()
        assert data["processed_count"] == 0
    
    def test_get_retention_status(self, client):
        """Test getting retention status."""
        response = client.get("/api/admin/retention/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["scheduler_running"] is True
        assert data["pending_gdpr_requests"] == 0
        assert data["overdue_gdpr_requests"] == 0


@pytest.mark.asyncio
async def test_trigger_retention_job_async():
    """Test retention API with async client."""
    app = FastAPI()
    app.include_router(router)
    
    configure_services(
        retention_service=MockRetentionService(),
        gdpr_service=MockGDPRService(),
        scheduler=MockScheduler(),
    )
    
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost:8080"
    ) as client:
        response = await client.post(
            "/api/admin/retention/trigger",
            json={"dry_run": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"