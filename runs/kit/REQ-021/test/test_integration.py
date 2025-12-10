"""
Integration tests for observability.

REQ-021: Observability instrumentation
"""

import pytest
import json
from io import StringIO
from unittest.mock import patch

from starlette.testclient import TestClient
from fastapi import FastAPI

from infra.observability import (
    configure_logging,
    get_logger,
    get_correlation_id,
    correlation_id_context,
    get_metrics_registry,
    trace_span,
)
from infra.observability.fastapi_integration import (
    setup_observability,
    create_observable_app,
)
from infra.observability.config import ObservabilityConfig, LoggingConfig, MetricsConfig, TracingConfig, LogLevel


class TestFastAPIIntegration:
    """Tests for FastAPI integration."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            logger = get_logger(__name__)
            logger.info("Test endpoint called")
            return {"status": "ok", "correlation_id": get_correlation_id()}
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        setup_observability(app)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app, raise_server_exceptions=False)
    
    def test_correlation_id_propagation(self, client):
        """Correlation ID should be propagated through request."""
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": "test-correlation-123"}
        )
        
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "test-correlation-123"
        assert response.json()["correlation_id"] == "test-correlation-123"
    
    def test_correlation_id_generated(self, client):
        """Correlation ID should be generated if not provided."""
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert response.json()["correlation_id"] is not None
    
    def test_metrics_endpoint(self, client):
        """Metrics endpoint should be available."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "voicesurveyagent" in response.text
    
    def test_health_endpoint(self, client):
        """Health endpoint should be available."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "unhealthy", "degraded"]
    
    def test_readiness_endpoint(self, client):
        """Readiness endpoint should be available."""
        response = client.get("/ready")
        
        assert response.status_code in [200, 503]
    
    def test_liveness_endpoint(self, client):
        """Liveness endpoint should be available."""
        response = client.get("/live")
        
        assert response.status_code == 200
        assert response.json()["status"] == "alive"
    
    def test_request_metrics_recorded(self, client):
        """Request metrics should be recorded."""
        # Make some requests
        client.get("/test")
        client.get("/test")
        client.get("/error")
        
        # Check metrics
        response = client.get("/metrics")
        content = response.text
        
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content


class TestCreateObservableApp:
    """Tests for create_observable_app helper."""
    
    def test_creates_configured_app(self):
        """Should create app with observability configured."""
        app = create_observable_app(
            title="Test App",
            version="1.0.0",
        )
        
        client = TestClient(app)
        
        # Check endpoints exist
        assert client.get("/health").status_code == 200
        assert client.get("/metrics").status_code == 200
        assert client.get("/live").status_code == 200


class TestEndToEndObservability:
    """End-to-end observability tests."""
    
    def test_full_request_flow(self):
        """Test complete observability flow for a request."""
        app = FastAPI()
        
        @app.get("/api/campaigns/{campaign_id}")
        async def get_campaign(campaign_id: str):
            logger = get_logger(__name__)
            
            with trace_span("fetch_campaign", {"campaign_id": campaign_id}) as span:
                logger.info(
                    "Fetching campaign",
                    campaign_id=campaign_id,
                )
                
                # Simulate some work
                registry = get_metrics_registry()
                registry.http_requests_total.inc(
                    method="GET",
                    endpoint="/api/campaigns/{id}",
                    status="200",
                )
                
                return {"id": campaign_id, "name": "Test Campaign"}
        
        setup_observability(app)
        client = TestClient(app)
        
        # Make request
        response = client.get(
            "/api/campaigns/camp-123",
            headers={"X-Correlation-ID": "e2e-test-456"}
        )
        
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "e2e-test-456"
        assert response.json()["id"] == "camp-123"
        
        # Verify metrics were recorded
        metrics_response = client.get("/metrics")
        assert "http_requests_total" in metrics_response.text