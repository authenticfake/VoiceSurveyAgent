"""
Health check endpoints.

REQ-021: Observability instrumentation
Provides health and readiness endpoints for Kubernetes probes.
"""

from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from starlette.requests import Request
from starlette.responses import JSONResponse


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


HealthCheckFunc = Callable[[], Awaitable[HealthCheckResult]]


class HealthChecker:
    """
    Health checker with pluggable checks.
    
    Supports multiple health checks for different dependencies.
    """
    
    def __init__(self):
        self._checks: Dict[str, HealthCheckFunc] = {}
    
    def register(self, name: str, check: HealthCheckFunc) -> None:
        """Register a health check."""
        self._checks[name] = check
    
    async def check_all(self) -> tuple[HealthStatus, Dict[str, Any]]:
        """
        Run all health checks.
        
        Returns:
            Tuple of (overall status, details dict).
        """
        results: Dict[str, Any] = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, check in self._checks.items():
            try:
                result = await check()
                results[name] = {
                    "status": result.status.value,
                    "message": result.message,
                    **result.details,
                }
                
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                results[name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": str(e),
                }
                overall_status = HealthStatus.UNHEALTHY
        
        return overall_status, results


# Global health checker
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


async def health_endpoint(request: Request) -> JSONResponse:
    """
    Health check endpoint.
    
    Returns 200 if healthy, 503 if unhealthy.
    """
    checker = get_health_checker()
    status, details = await checker.check_all()
    
    response_data = {
        "status": status.value,
        "checks": details,
    }
    
    status_code = 200 if status == HealthStatus.HEALTHY else 503
    return JSONResponse(content=response_data, status_code=status_code)


async def readiness_endpoint(request: Request) -> JSONResponse:
    """
    Readiness check endpoint.
    
    Returns 200 if ready to accept traffic, 503 otherwise.
    """
    checker = get_health_checker()
    status, details = await checker.check_all()
    
    response_data = {
        "status": status.value,
        "checks": details,
    }
    
    # Only return 200 if fully healthy
    status_code = 200 if status == HealthStatus.HEALTHY else 503
    return JSONResponse(content=response_data, status_code=status_code)


async def liveness_endpoint(request: Request) -> JSONResponse:
    """
    Liveness check endpoint.
    
    Simple check that the application is running.
    """
    return JSONResponse(content={"status": "alive"}, status_code=200)


# Common health check implementations

async def database_health_check(
    check_connection: Callable[[], Awaitable[bool]],
) -> HealthCheckResult:
    """
    Database health check factory.
    
    Args:
        check_connection: Async function that returns True if DB is connected.
    """
    try:
        is_connected = await check_connection()
        if is_connected:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection OK",
            )
        else:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message="Database connection failed",
            )
    except Exception as e:
        return HealthCheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database error: {str(e)}",
        )


async def redis_health_check(
    check_connection: Callable[[], Awaitable[bool]],
) -> HealthCheckResult:
    """
    Redis health check factory.
    
    Args:
        check_connection: Async function that returns True if Redis is connected.
    """
    try:
        is_connected = await check_connection()
        if is_connected:
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection OK",
            )
        else:
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message="Redis connection failed",
            )
    except Exception as e:
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis error: {str(e)}",
        )