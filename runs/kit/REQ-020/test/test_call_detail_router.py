"""
Integration tests for call detail API router (REQ-020).

Tests the HTTP layer including authentication and authorization.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.calls.exceptions import CallAccessDeniedError, CallNotFoundError
from app.calls.models import CallAttemptOutcome, CallDetailResponse, TranscriptSnippet
from app.calls.router import (
    CurrentUser,
    get_call_detail_service,
    get_current_user,
    router as calls_router,
)
from app.calls.service import CallDetailService


class FakeCallDetailService:
    """Fake service for testing router."""
    
    def __init__(self):
        self.calls: dict[str, CallDetailResponse] = {}
        self.access_denied_calls: set[str] = set()
    
    def add_call(self, response: CallDetailResponse) -> None:
        """Add a call response to the fake store."""
        self.calls[response.call_id] = response
    
    def deny_access(self, call_id: str) -> None:
        """Mark a call as access denied."""
        self.access_denied_calls.add(call_id)
    
    async def get_call_detail(self, call_id: str, user_id: UUID) -> CallDetailResponse:
        """Get call detail, raising appropriate exceptions."""
        if call_id in self.access_denied_calls:
            raise CallAccessDeniedError(call_id, "User does not have access")
        if call_id not in self.calls:
            raise CallNotFoundError(call_id)
        return self.calls[call_id]


def make_call_response(
    call_id: str = "call-test-123",
    outcome: CallAttemptOutcome = CallAttemptOutcome.COMPLETED,
    with_transcript: bool = False,
    with_recording: bool = False,
) -> CallDetailResponse:
    """Factory for creating test call responses."""
    transcript = None
    if with_transcript:
        transcript = TranscriptSnippet(
            text="Hello, this is a survey...",
            language="en",
            created_at=datetime(2024, 1, 15, 10, 35, 1, tzinfo=timezone.utc),
        )
    
    recording_url = None
    if with_recording:
        recording_url = "https://recordings.example.com/abc123"
    
    return CallDetailResponse(
        call_id=call_id,
        contact_id=uuid4(),
        campaign_id=uuid4(),
        attempt_number=1,
        provider_call_id="CA123456",
        outcome=outcome,
        started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        answered_at=datetime(2024, 1, 15, 10, 30, 15, tzinfo=timezone.utc),
        ended_at=datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
        error_code=None,
        provider_raw_status="completed",
        transcript_snippet=transcript,
        recording_url=recording_url,
    )


def create_test_app(
    fake_service: FakeCallDetailService,
    user: Optional[CurrentUser] = None,
) -> FastAPI:
    """Create a test FastAPI app with overridden dependencies."""
    app = FastAPI()
    app.include_router(calls_router)
    
    async def override_get_current_user() -> CurrentUser:
        if user is None:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        return user
    
    async def override_get_service() -> CallDetailService:
        return fake_service  # type: ignore
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_call_detail_service] = override_get_service
    
    return app


class TestCallDetailRouter:
    """Tests for call detail API router."""
    
    @pytest.fixture
    def fake_service(self) -> FakeCallDetailService:
        """Create a fake service."""
        return FakeCallDetailService()
    
    @pytest.fixture
    def admin_user(self) -> CurrentUser:
        """Create an admin user."""
        return CurrentUser(user_id=uuid4(), role="admin")
    
    @pytest.fixture
    def campaign_manager_user(self) -> CurrentUser:
        """Create a campaign manager user."""
        return CurrentUser(user_id=uuid4(), role="campaign_manager")
    
    @pytest.fixture
    def viewer_user(self) -> CurrentUser:
        """Create a viewer user."""
        return CurrentUser(user_id=uuid4(), role="viewer")
    
    @pytest.mark.asyncio
    async def test_get_call_detail_success_admin(
        self, fake_service: FakeCallDetailService, admin_user: CurrentUser
    ):
        """Test successful call detail retrieval as admin."""
        # Arrange
        call_response = make_call_response(call_id="call-admin-test")
        fake_service.add_call(call_response)
        app = create_test_app(fake_service, admin_user)
        
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/calls/call-admin-test")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["call_id"] == "call-admin-test"
        assert data["outcome"] == "completed"
    
    @pytest.mark.asyncio
    async def test_get_call_detail_success_campaign_manager(
        self, fake_service: FakeCallDetailService, campaign_manager_user: CurrentUser
    ):
        """Test successful call detail retrieval as campaign manager."""
        # Arrange
        call_response = make_call_response(call_id="call-cm-test")
        fake_service.add_call(call_response)
        app = create_test_app(fake_service, campaign_manager_user)
        
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/calls/call-cm-test")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["call_id"] == "call-cm-test"
    
    @pytest.mark.asyncio
    async def test_get_call_detail_forbidden_viewer(
        self, fake_service: FakeCallDetailService, viewer_user: CurrentUser
    ):
        """Test viewer role is denied access."""
        # Arrange
        call_response = make_call_response(call_id="call-viewer-test")
        fake_service.add_call(call_response)
        app = create_test_app(fake_service, viewer_user)
        
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/calls/call-viewer-test")
        
        # Assert
        assert response.status_code == 403
        assert "campaign_manager" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_call_detail_unauthorized(
        self, fake_service: FakeCallDetailService
    ):
        """Test unauthenticated request is rejected."""
        # Arrange
        app = create_test_app(fake_service, user=None)
        
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/calls/any-call")
        
        # Assert
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_call_detail_not_found(
        self, fake_service: FakeCallDetailService, admin_user: CurrentUser
    ):
        """Test 404 for non-existent call."""
        # Arrange
        app = create_test_app(fake_service, admin_user)
        
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/calls/non-existent-call")
        
        # Assert
        assert response.status_code == 404
        assert "non-existent-call" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_call_detail_with_transcript(
        self, fake_service: FakeCallDetailService, admin_user: CurrentUser
    ):
        """Test response includes transcript when available."""
        # Arrange
        call_response = make_call_response(
            call_id="call-with-transcript",
            with_transcript=True,
        )
        fake_service.add_call(call_response)
        app = create_test_app(fake_service, admin_user)
        
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/calls/call-with-transcript")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["transcript_snippet"] is not None
        assert data["transcript_snippet"]["text"] == "Hello, this is a survey..."
        assert data["transcript_snippet"]["language"] == "en"
    
    @pytest.mark.asyncio
    async def test_get_call_detail_with_recording(
        self, fake_service: FakeCallDetailService, admin_user: CurrentUser
    ):
        """Test response includes recording URL when available."""
        # Arrange
        call_response = make_call_response(
            call_id="call-with-recording",
            with_recording=True,
        )
        fake_service.add_call(call_response)
        app = create_test_app(fake_service, admin_user)
        
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/calls/call-with-recording")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["recording_url"] == "https://recordings.example.com/abc123"
    
    @pytest.mark.asyncio
    async def test_get_call_detail_all_fields(
        self, fake_service: FakeCallDetailService, admin_user: CurrentUser
    ):
        """Test response includes all expected fields."""
        # Arrange
        call_response = make_call_response(
            call_id="call-full-test",
            with_transcript=True,
            with_recording=True,
        )
        fake_service.add_call(call_response)
        app = create_test_app(fake_service, admin_user)
        
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/calls/call-full-test")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields are present
        assert "call_id" in data
        assert "contact_id" in data
        assert "campaign_id" in data
        assert "attempt_number" in data
        assert "provider_call_id" in data
        assert "outcome" in data
        assert "started_at" in data
        assert "answered_at" in data
        assert "ended_at" in data
        assert "error_code" in data
        assert "provider_raw_status" in data
        assert "transcript_snippet" in data
        assert "recording_url" in data
    
    @pytest.mark.asyncio
    async def test_get_call_detail_campaign_access_denied(
        self, fake_service: FakeCallDetailService, admin_user: CurrentUser
    ):
        """Test 403 when user lacks campaign access."""
        # Arrange
        call_response = make_call_response(call_id="call-restricted")
        fake_service.add_call(call_response)
        fake_service.deny_access("call-restricted")
        app = create_test_app(fake_service, admin_user)
        
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/calls/call-restricted")
        
        # Assert
        assert response.status_code == 403