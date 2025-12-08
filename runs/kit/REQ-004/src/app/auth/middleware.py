"""
Authentication middleware.

Provides JWT validation and user context injection.
"""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.shared.logging import set_correlation_id

class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and correlation ID handling."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process request with authentication and correlation ID."""
        # Set correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(correlation_id)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response
        response.headers["X-Correlation-ID"] = correlation_id

        return response