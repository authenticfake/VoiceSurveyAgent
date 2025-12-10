"""
Tests for correlation ID management.

REQ-021: Observability instrumentation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from infra.observability.correlation import (
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
    correlation_id_context,
    CorrelationIdMiddleware,
    inject_correlation_headers,
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
)


class TestCorrelationIdFunctions:
    """Tests for correlation ID utility functions."""
    
    def test_generate_correlation_id(self):
        """Generated IDs should be valid UUIDs."""
        cid = generate_correlation_id()
        assert len(cid) == 36  # UUID format
        assert cid.count("-") == 4
    
    def test_generate_unique_ids(self):
        """Each generated ID should be unique."""
        ids = [generate_correlation_id() for _ in range(100)]
        assert len(set(ids)) == 100
    
    def test_set_and_get_correlation_id(self):
        """Set and get should work correctly."""
        set_correlation_id("test-id-123")
        assert get_correlation_id() == "test-id-123"
    
    def test_correlation_id_context(self):
        """Context manager should set and reset ID."""
        original = get_correlation_id()
        
        with correlation_id_context("context-id-456") as cid:
            assert cid == "context-id-456"
            assert get_correlation_id() == "context-id-456"
        
        # Should be reset after context
        assert get_correlation_id() == original
    
    def test_correlation_id_context_generates_id(self):
        """Context manager should generate ID if not provided."""
        with correlation_id_context() as cid:
            assert cid is not None
            assert len(cid) == 36
            assert get_correlation_id() == cid
    
    def test_inject_correlation_headers(self):
        """Headers should include correlation ID."""
        with correlation_id_context("inject-test-789"):
            headers = inject_correlation_headers({"Content-Type": "application/json"})
            
            assert headers["Content-Type"] == "application/json"
            assert headers[CORRELATION_ID_HEADER] == "inject-test-789"
    
    def test_inject_headers_no_correlation_id(self):
        """Headers should be unchanged if no correlation ID."""
        # Reset correlation ID
        set_correlation_id(None)  # type: ignore
        
        original = {"Content-Type": "application/json"}
        headers = inject_correlation_headers(original)
        
        # Should not add header if no correlation ID
        assert CORRELATION_ID_HEADER not in headers or headers.get(CORRELATION_ID_HEADER) is None


class TestCorrelationIdMiddleware:
    """Tests for correlation ID middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test application with middleware."""
        async def homepage(request):
            cid = get_correlation_id()
            return JSONResponse({"correlation_id": cid})
        
        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(CorrelationIdMiddleware)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_generates_correlation_id(self, client):
        """Should generate correlation ID if not provided."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert CORRELATION_ID_HEADER in response.headers
        
        data = response.json()
        assert data["correlation_id"] == response.headers[CORRELATION_ID_HEADER]
    
    def test_uses_provided_correlation_id(self, client):
        """Should use correlation ID from header."""
        response = client.get(
            "/",
            headers={CORRELATION_ID_HEADER: "provided-id-123"}
        )
        
        assert response.status_code == 200
        assert response.headers[CORRELATION_ID_HEADER] == "provided-id-123"
        
        data = response.json()
        assert data["correlation_id"] == "provided-id-123"
    
    def test_uses_request_id_header(self, client):
        """Should fall back to X-Request-ID header."""
        response = client.get(
            "/",
            headers={REQUEST_ID_HEADER: "request-id-456"}
        )
        
        assert response.status_code == 200
        assert response.headers[CORRELATION_ID_HEADER] == "request-id-456"
    
    def test_prefers_correlation_id_over_request_id(self, client):
        """Should prefer X-Correlation-ID over X-Request-ID."""
        response = client.get(
            "/",
            headers={
                CORRELATION_ID_HEADER: "correlation-id",
                REQUEST_ID_HEADER: "request-id",
            }
        )
        
        assert response.headers[CORRELATION_ID_HEADER] == "correlation-id"