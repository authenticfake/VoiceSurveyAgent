"""
Unit tests for RBAC access denial logging.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from fastapi import Request

from app.auth.rbac.logging import (
    log_access_denied,
    _get_client_ip,
    AccessDenialAuditHandler,
    setup_rbac_logging,
)


def create_mock_request(
    method: str = "GET",
    path: str = "/test",
    headers: dict = None,
    client_host: str = "127.0.0.1",
):
    """Create a mock request for testing."""
    request = MagicMock(spec=Request)
    request.method = method
    request.url = MagicMock()
    request.url.path = path
    request.query_params = {}
    request.headers = headers or {}
    request.client = MagicMock()
    request.client.host = client_host
    return request


class TestLogAccessDenied:
    """Tests for log_access_denied function."""
    
    @pytest.mark.asyncio
    @patch("app.auth.rbac.logging.logger")
    async def test_basic_logging(self, mock_logger):
        """Test basic access denial logging."""
        await log_access_denied(
            user_id="user-123",
            endpoint="GET /api/admin/config",
            required_role="admin",
            user_role="viewer",
        )
        
        mock_logger.warning.assert_called_once()
        log_message = mock_logger.warning.call_args[0][0]
        log_data = json.loads(log_message)
        
        assert log_data["event"] == "access_denied"
        assert log_data["user_id"] == "user-123"
        assert log_data["endpoint"] == "GET /api/admin/config"
        assert log_data["required_role"] == "admin"
        assert log_data["user_role"] == "viewer"
        assert "timestamp" in log_data
    
    @pytest.mark.asyncio
    @patch("app.auth.rbac.logging.logger")
    async def test_logging_with_request_context(self, mock_logger):
        """Test logging includes request context."""
        request = create_mock_request(
            method="POST",
            path="/api/campaigns",
            headers={
                "user-agent": "TestClient/1.0",
                "x-correlation-id": "corr-123",
            },
        )
        
        await log_access_denied(
            user_id="user-456",
            endpoint="POST /api/campaigns",
            required_role="campaign_manager",
            user_role="viewer",
            request=request,
        )
        
        log_message = mock_logger.warning.call_args[0][0]
        log_data = json.loads(log_message)
        
        assert "request_context" in log_data
        ctx = log_data["request_context"]
        assert ctx["method"] == "POST"
        assert ctx["path"] == "/api/campaigns"
        assert ctx["user_agent"] == "TestClient/1.0"
        assert ctx["correlation_id"] == "corr-123"
        assert ctx["client_ip"] == "127.0.0.1"
    
    @pytest.mark.asyncio
    @patch("app.auth.rbac.logging.logger")
    async def test_logging_with_additional_context(self, mock_logger):
        """Test logging includes additional context."""
        await log_access_denied(
            user_id="user-789",
            endpoint="DELETE /api/exclusions/123",
            required_role="admin",
            user_role="campaign_manager",
            additional_context={"resource_id": "123", "action": "delete"},
        )
        
        log_message = mock_logger.warning.call_args[0][0]
        log_data = json.loads(log_message)
        
        assert "additional_context" in log_data
        assert log_data["additional_context"]["resource_id"] == "123"
        assert log_data["additional_context"]["action"] == "delete"


class TestGetClientIp:
    """Tests for _get_client_ip function."""
    
    def test_x_forwarded_for_header(self):
        """Test extraction from X-Forwarded-For header."""
        request = create_mock_request(
            headers={"x-forwarded-for": "203.0.113.1, 198.51.100.1"}
        )
        
        ip = _get_client_ip(request)
        
        assert ip == "203.0.113.1"
    
    def test_x_real_ip_header(self):
        """Test extraction from X-Real-IP header."""
        request = create_mock_request(
            headers={"x-real-ip": "203.0.113.2"}
        )
        
        ip = _get_client_ip(request)
        
        assert ip == "203.0.113.2"
    
    def test_direct_client(self):
        """Test extraction from direct client."""
        request = create_mock_request(client_host="192.168.1.1")
        
        ip = _get_client_ip(request)
        
        assert ip == "192.168.1.1"
    
    def test_no_client(self):
        """Test when no client info available."""
        request = create_mock_request()
        request.client = None
        
        ip = _get_client_ip(request)
        
        assert ip is None


class TestAccessDenialAuditHandler:
    """Tests for AccessDenialAuditHandler."""
    
    def test_emit_stores_json_events(self):
        """Test that JSON events are stored."""
        handler = AccessDenialAuditHandler()
        
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg=json.dumps({"event": "access_denied", "user_id": "test"}),
            args=(),
            exc_info=None,
        )
        
        handler.emit(record)
        
        events = handler.get_recent_denials()
        assert len(events) == 1
        assert events[0]["event"] == "access_denied"
        assert events[0]["user_id"] == "test"
    
    def test_emit_ignores_non_json(self):
        """Test that non-JSON messages are ignored."""
        handler = AccessDenialAuditHandler()
        
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Plain text message",
            args=(),
            exc_info=None,
        )
        
        handler.emit(record)
        
        events = handler.get_recent_denials()
        assert len(events) == 0
    
    def test_get_recent_denials_limit(self):
        """Test that get_recent_denials respects limit."""
        handler = AccessDenialAuditHandler()
        
        import logging
        for i in range(10):
            record = logging.LogRecord(
                name="test",
                level=logging.WARNING,
                pathname="",
                lineno=0,
                msg=json.dumps({"event": "access_denied", "index": i}),
                args=(),
                exc_info=None,
            )
            handler.emit(record)
        
        events = handler.get_recent_denials(limit=5)
        assert len(events) == 5
        # Should be the last 5 events
        assert events[0]["index"] == 5
        assert events[4]["index"] == 9