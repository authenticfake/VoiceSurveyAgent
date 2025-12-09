"""
Integration tests for webhook router.

REQ-010: Telephony webhook handler
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.telephony.webhooks.router import router

@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
def mock_call_attempt() -> MagicMock:
    """Create mock call attempt."""
    attempt = MagicMock()
    attempt.id = uuid4()
    attempt.call_id = "test-call-123"
    attempt.contact_id = uuid4()
    attempt.campaign_id = uuid4()
    attempt.attempt_number = 1
    attempt.metadata = {}
    attempt.outcome = None
    attempt.provider_raw_status = None
    attempt.answered_at = None
    attempt.ended_at = None
    attempt.error_code = None
    return attempt

@pytest.mark.asyncio
async def test_receive_webhook_event_success(
    app: FastAPI,
    mock_call_attempt: MagicMock,
) -> None:
    """Test successful webhook event processing."""
    campaign_id = mock_call_attempt.campaign_id
    contact_id = mock_call_attempt.contact_id

    # Mock database session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_call_attempt
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    with patch(
        "app.telephony.webhooks.router.get_db_session",
        return_value=mock_session,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/webhooks/telephony/events?call_id=test-call-123&campaign_id={campaign_id}&contact_id={contact_id}",
                data={
                    "CallSid": "CA123456",
                    "CallStatus": "in-progress",
                    "From": "+14155551234",
                    "To": "+14155555678",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["call_id"] == "test-call-123"
    assert data["event_type"] == "call.answered"

@pytest.mark.asyncio
async def test_receive_webhook_event_invalid_payload(app: FastAPI) -> None:
    """Test webhook with invalid payload returns 400."""
    mock_session = AsyncMock()

    with patch(
        "app.telephony.webhooks.router.get_db_session",
        return_value=mock_session,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/webhooks/telephony/events",
                data={
                    "CallStatus": "in-progress",
                    # Missing CallSid and metadata
                },
            )

    assert response.status_code == 400
    assert "Invalid webhook payload" in response.json()["detail"]

@pytest.mark.asyncio
async def test_receive_webhook_event_duplicate(
    app: FastAPI,
    mock_call_attempt: MagicMock,
) -> None:
    """Test duplicate webhook event returns duplicate status."""
    campaign_id = mock_call_attempt.campaign_id
    contact_id = mock_call_attempt.contact_id

    # Mark event as already processed
    mock_call_attempt.metadata = {"processed_events": ["call.answered"]}

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_call_attempt
    mock_session.execute.return_value = mock_result

    with patch(
        "app.telephony.webhooks.router.get_db_session",
        return_value=mock_session,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/webhooks/telephony/events?call_id=test-call-123&campaign_id={campaign_id}&contact_id={contact_id}",
                data={
                    "CallSid": "CA123456",
                    "CallStatus": "in-progress",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "duplicate"