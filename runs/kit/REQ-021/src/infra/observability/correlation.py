"""
Correlation ID management for request tracing.

REQ-021: Observability instrumentation
- Correlation ID propagated across HTTP, telephony, LLM calls
"""

import uuid
from contextvars import ContextVar
from typing import Optional, Callable, Any
from contextlib import contextmanager

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


# Context variable for correlation ID
_correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Header names for correlation ID propagation
CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in context."""
    _correlation_id_var.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


@contextmanager
def correlation_id_context(correlation_id: Optional[str] = None):
    """
    Context manager for correlation ID scope.
    
    Args:
        correlation_id: Optional correlation ID. If None, generates a new one.
        
    Yields:
        The correlation ID being used.
    """
    cid = correlation_id or generate_correlation_id()
    token = _correlation_id_var.set(cid)
    try:
        yield cid
    finally:
        _correlation_id_var.reset(token)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract or generate correlation ID for each request.
    
    Extracts correlation ID from incoming headers or generates a new one.
    Adds correlation ID to response headers.
    """
    
    def __init__(
        self,
        app: Any,
        header_name: str = CORRELATION_ID_HEADER,
        generator: Callable[[], str] = generate_correlation_id,
    ):
        super().__init__(app)
        self.header_name = header_name
        self.generator = generator
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request with correlation ID."""
        # Extract from header or generate new
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = request.headers.get(REQUEST_ID_HEADER)
        if not correlation_id:
            correlation_id = self.generator()
        
        # Set in context
        token = _correlation_id_var.set(correlation_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add to response headers
            response.headers[self.header_name] = correlation_id
            
            return response
        finally:
            _correlation_id_var.reset(token)


def inject_correlation_headers(headers: dict) -> dict:
    """
    Inject correlation ID into outgoing request headers.
    
    Use this when making HTTP calls to external services.
    
    Args:
        headers: Existing headers dict.
        
    Returns:
        Headers dict with correlation ID added.
    """
    correlation_id = get_correlation_id()
    if correlation_id:
        headers = dict(headers)
        headers[CORRELATION_ID_HEADER] = correlation_id
    return headers