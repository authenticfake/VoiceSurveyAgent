"""
Tests for health check endpoints.

REQ-021: Observability instrumentation
"""

import pytest
from unittest.mock import AsyncMock

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route

from infra.observability.health import (
    HealthStatus,
    HealthCheckResult,
    HealthChecker,
    get_health_checker,
    health_endpoint,
    readiness_endpoint,
    liveness_endpoint,
    database_health_check,
    redis_health_check,
)


class TestHealthCheckResult:
    """Tests for HealthCheckResult."""
    
    def test_healthy_result(self):
        """Healthy result should have correct status."""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All good",
        )
        
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
    
    def test_unhealthy_result(self):
        """Unhealthy result should have correct status."""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.UNHEALTHY,
            message="Connection failed",
        )
        
        assert result.status == HealthStatus.UNHEALTHY


class TestHealthChecker:
    """Tests for HealthChecker."""
    
    @pytest.fixture
    def checker(self):
        """Create fresh health checker."""
        return HealthChecker()
    
    @pytest.mark.asyncio
    async def test_check_all_healthy(self, checker):
        """All healthy checks should return healthy status."""
        async def healthy_check():
            return HealthCheckResult(
                name="test",
                status=HealthStatus.HEALTHY,
            )
        
        checker.register("test", healthy_check)
        
        status, details = await checker.check_all()
        
        assert status == HealthStatus.HEALTHY
        assert details["test"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_check_all_unhealthy(self, checker):
        """Unhealthy check should return unhealthy status."""
        async def unhealthy_check():
            return HealthCheckResult(
                name="test",
                status=HealthStatus.UNHEALTHY,
                message="Failed",
            )
        
        checker.register("test", unhealthy_check)
        
        status, details = await checker.check_all()
        
        assert status == HealthStatus.UNHEALTHY
        assert details["test"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_check_all_degraded(self, checker):
        """Degraded check should return degraded status."""
        async def degraded_check():
            return HealthCheckResult(
                name="test",
                status=HealthStatus.DEGRADED,
            )
        
        checker.register("test", degraded_check)
        
        status, details = await checker.check_all()
        
        assert status == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_check_handles_exception(self, checker):
        """Exception in check should return unhealthy."""
        async def failing_check():
            raise RuntimeError("Check failed")
        
        checker.register("test", failing_check)
        
        status, details = await checker.check_all()
        
        assert status == HealthStatus.UNHEALTHY
        assert "Check failed" in details["test"]["message"]
    
    @pytest.mark.asyncio
    async def test_multiple_checks(self, checker):
        """Multiple checks should all be evaluated."""
        async def healthy_check():
            return HealthCheckResult(name="healthy", status=HealthStatus.HEALTHY)
        
        async def unhealthy_check():
            return HealthCheckResult(name="unhealthy", status=HealthStatus.UNHEALTHY)
        
        checker.register("healthy", healthy_check)
        checker.register("unhealthy", unhealthy_check)
        
        status, details = await checker.check_all()
        
        assert status == HealthStatus.UNHEALTHY
        assert "healthy" in details
        assert "unhealthy" in details


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test application with health endpoints."""
        app = Starlette(routes=[
            Route("/health", health_endpoint),
            Route("/ready", readiness_endpoint),
            Route("/live", liveness_endpoint),
        ])
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_liveness_endpoint(self, client):
        """Liveness endpoint should always return 200."""
        response = client.get("/live")
        
        assert response.status_code == 200
        assert response.json()["status"] == "alive"
    
    def test_health_endpoint_healthy(self, client):
        """Health endpoint should return 200 when healthy."""
        # Reset global checker
        import infra.observability.health as health_module
        health_module._health_checker = HealthChecker()
        
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_readiness_endpoint_healthy(self, client):
        """Readiness endpoint should return 200 when healthy."""
        import infra.observability.health as health_module
        health_module._health_checker = HealthChecker()
        
        response = client.get("/ready")
        
        assert response.status_code == 200


class TestHealthCheckFactories:
    """Tests for health check factory functions."""
    
    @pytest.mark.asyncio
    async def test_database_health_check_healthy(self):
        """Database health check should return healthy when connected."""
        check_connection = AsyncMock(return_value=True)
        
        result = await database_health_check(check_connection)
        
        assert result.status == HealthStatus.HEALTHY
        assert "OK" in result.message
    
    @pytest.mark.asyncio
    async def test_database_health_check_unhealthy(self):
        """Database health check should return unhealthy when disconnected."""
        check_connection = AsyncMock(return_value=False)
        
        result = await database_health_check(check_connection)
        
        assert result.status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_database_health_check_exception(self):
        """Database health check should handle exceptions."""
        check_connection = AsyncMock(side_effect=RuntimeError("Connection error"))
        
        result = await database_health_check(check_connection)
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection error" in result.message
    
    @pytest.mark.asyncio
    async def test_redis_health_check_healthy(self):
        """Redis health check should return healthy when connected."""
        check_connection = AsyncMock(return_value=True)
        
        result = await redis_health_check(check_connection)
        
        assert result.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_redis_health_check_unhealthy(self):
        """Redis health check should return unhealthy when disconnected."""
        check_connection = AsyncMock(return_value=False)
        
        result = await redis_health_check(check_connection)
        
        assert result.status == HealthStatus.UNHEALTHY