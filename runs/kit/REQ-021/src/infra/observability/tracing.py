"""
OpenTelemetry tracing integration.

REQ-021: Observability instrumentation
- OpenTelemetry traces for API requests
- Traces span across async operations
"""

import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, field
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from infra.observability.config import get_observability_config
from infra.observability.correlation import get_correlation_id


F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class SpanContext:
    """Span context for trace propagation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    sampled: bool = True


@dataclass
class Span:
    """
    Represents a trace span.
    
    Simplified span implementation for basic tracing.
    Can be replaced with full OpenTelemetry SDK when available.
    """
    name: str
    context: SpanContext
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: list = field(default_factory=list)
    status: str = "OK"
    status_message: Optional[str] = None
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": time.perf_counter(),
            "attributes": attributes or {},
        })
    
    def set_status(self, status: str, message: Optional[str] = None) -> None:
        """Set span status."""
        self.status = status
        self.status_message = message
    
    def end(self) -> None:
        """End the span."""
        self.end_time = time.perf_counter()
    
    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time is None:
            return (time.perf_counter() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for logging/export."""
        return {
            "name": self.name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.context.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
            "status_message": self.status_message,
        }


class Tracer:
    """
    Simple tracer implementation.
    
    Provides basic span creation and context propagation.
    Can be replaced with OpenTelemetry Tracer when SDK is available.
    """
    
    def __init__(self, service_name: str, sample_rate: float = 1.0):
        self.service_name = service_name
        self.sample_rate = sample_rate
        self._current_span: Optional[Span] = None
    
    def _should_sample(self) -> bool:
        """Determine if this trace should be sampled."""
        import random
        return random.random() < self.sample_rate
    
    def _generate_id(self) -> str:
        """Generate a trace/span ID."""
        return uuid.uuid4().hex[:16]
    
    def start_span(
        self,
        name: str,
        parent: Optional[Span] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        Start a new span.
        
        Args:
            name: Span name.
            parent: Optional parent span.
            attributes: Initial span attributes.
            
        Returns:
            New Span instance.
        """
        # Determine trace context
        if parent:
            trace_id = parent.context.trace_id
            parent_span_id = parent.context.span_id
            sampled = parent.context.sampled
        else:
            # Use correlation ID as trace ID if available
            correlation_id = get_correlation_id()
            trace_id = correlation_id.replace("-", "")[:32] if correlation_id else self._generate_id() * 2
            parent_span_id = None
            sampled = self._should_sample()
        
        context = SpanContext(
            trace_id=trace_id,
            span_id=self._generate_id(),
            parent_span_id=parent_span_id,
            sampled=sampled,
        )
        
        span = Span(name=name, context=context)
        
        # Set service name attribute
        span.set_attribute("service.name", self.service_name)
        
        # Set initial attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        self._current_span = span
        return span
    
    @contextmanager
    def span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for creating spans.
        
        Args:
            name: Span name.
            attributes: Initial span attributes.
            
        Yields:
            The created span.
        """
        parent = self._current_span
        span = self.start_span(name, parent=parent, attributes=attributes)
        try:
            yield span
        except Exception as e:
            span.set_status("ERROR", str(e))
            raise
        finally:
            span.end()
            self._current_span = parent
            
            # Log span if sampled
            if span.context.sampled:
                self._export_span(span)
    
    def _export_span(self, span: Span) -> None:
        """Export span (log it for now, can be extended to OTLP)."""
        from infra.observability.logging import get_logger
        logger = get_logger("tracing")
        logger.debug(
            f"Span completed: {span.name}",
            span=span.to_dict(),
        )


# Global tracer instance
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        config = get_observability_config().tracing
        _tracer = Tracer(
            service_name=config.service_name,
            sample_rate=config.sample_rate,
        )
    return _tracer


def configure_tracing(
    service_name: Optional[str] = None,
    sample_rate: Optional[float] = None,
) -> None:
    """
    Configure the tracing system.
    
    Args:
        service_name: Service name for spans.
        sample_rate: Sampling rate (0.0 to 1.0).
    """
    global _tracer
    config = get_observability_config().tracing
    
    _tracer = Tracer(
        service_name=service_name or config.service_name,
        sample_rate=sample_rate if sample_rate is not None else config.sample_rate,
    )


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Convenience function for creating trace spans.
    
    Args:
        name: Span name.
        attributes: Initial span attributes.
        
    Yields:
        The created span.
    """
    tracer = get_tracer()
    with tracer.span(name, attributes=attributes) as span:
        yield span


def traced(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """
    Decorator to trace a function.
    
    Args:
        name: Span name (defaults to function name).
        attributes: Initial span attributes.
    """
    def decorator(func: F) -> F:
        span_name = name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_span(span_name, attributes=attributes) as span:
                span.set_attribute("function", func.__name__)
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_span(span_name, attributes=attributes) as span:
                span.set_attribute("function", func.__name__)
                return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to create spans for HTTP requests.
    
    Creates a span for each incoming request with relevant attributes.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request with tracing."""
        config = get_observability_config().tracing
        if not config.enabled:
            return await call_next(request)
        
        tracer = get_tracer()
        
        # Create span for request
        span_name = f"{request.method} {request.url.path}"
        attributes = {
            "http.method": request.method,
            "http.url": str(request.url),
            "http.route": request.url.path,
            "http.scheme": request.url.scheme,
            "http.host": request.url.hostname or "",
            "http.user_agent": request.headers.get("user-agent", ""),
        }
        
        with tracer.span(span_name, attributes=attributes) as span:
            try:
                response = await call_next(request)
                span.set_attribute("http.status_code", response.status_code)
                
                if response.status_code >= 400:
                    span.set_status("ERROR", f"HTTP {response.status_code}")
                
                return response
            except Exception as e:
                span.set_status("ERROR", str(e))
                raise