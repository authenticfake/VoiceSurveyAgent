"""
Tests for distributed tracing.

REQ-021: Observability instrumentation
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from infra.observability.tracing import (
    Span,
    SpanContext,
    Tracer,
    get_tracer,
    configure_tracing,
    trace_span,
    traced,
    TracingMiddleware,
)
from infra.observability.correlation import correlation_id_context


class TestSpan:
    """Tests for Span class."""
    
    def test_span_creation(self):
        """Span should be created with correct attributes."""
        context = SpanContext(
            trace_id="trace123",
            span_id="span456",
        )
        span = Span(name="test-span", context=context)
        
        assert span.name == "test-span"
        assert span.context.trace_id == "trace123"
        assert span.context.span_id == "span456"
        assert span.status == "OK"
    
    def test_span_set_attribute(self):
        """Span should store attributes."""
        context = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=context)
        
        span.set_attribute("key1", "value1")
        span.set_attribute("key2", 42)
        
        assert span.attributes["key1"] == "value1"
        assert span.attributes["key2"] == 42
    
    def test_span_add_event(self):
        """Span should store events."""
        context = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=context)
        
        span.add_event("event1", {"detail": "value"})
        
        assert len(span.events) == 1
        assert span.events[0]["name"] == "event1"
        assert span.events[0]["attributes"]["detail"] == "value"
    
    def test_span_set_status(self):
        """Span should update status."""
        context = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=context)
        
        span.set_status("ERROR", "Something went wrong")
        
        assert span.status == "ERROR"
        assert span.status_message == "Something went wrong"
    
    def test_span_duration(self):
        """Span should calculate duration."""
        context = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=context)
        
        time.sleep(0.01)
        span.end()
        
        assert span.duration_ms > 0
        assert span.end_time is not None
    
    def test_span_to_dict(self):
        """Span should convert to dictionary."""
        context = SpanContext(
            trace_id="trace123",
            span_id="span456",
            parent_span_id="parent789",
        )
        span = Span(name="test-span", context=context)
        span.set_attribute("key", "value")
        span.end()
        
        data = span.to_dict()
        
        assert data["name"] == "test-span"
        assert data["trace_id"] == "trace123"
        assert data["span_id"] == "span456"
        assert data["parent_span_id"] == "parent789"
        assert data["attributes"]["key"] == "value"


class TestTracer:
    """Tests for Tracer class."""
    
    def test_tracer_start_span(self):
        """Tracer should create spans."""
        tracer = Tracer(service_name="test-service")
        
        span = tracer.start_span("test-operation")
        
        assert span.name == "test-operation"
        assert span.attributes["service.name"] == "test-service"
    
    def test_tracer_span_context_manager(self):
        """Tracer span context manager should work."""
        tracer = Tracer(service_name="test-service")
        
        with tracer.span("test-operation") as span:
            span.set_attribute("key", "value")
        
        assert span.end_time is not None
        assert span.attributes["key"] == "value"
    
    def test_tracer_nested_spans(self):
        """Tracer should handle nested spans."""
        tracer = Tracer(service_name="test-service")
        
        with tracer.span("parent") as parent_span:
            with tracer.span("child") as child_span:
                pass
        
        assert child_span.context.parent_span_id == parent_span.context.span_id
        assert child_span.context.trace_id == parent_span.context.trace_id
    
    def test_tracer_uses_correlation_id(self):
        """Tracer should use correlation ID as trace ID."""
        tracer = Tracer(service_name="test-service")
        
        with correlation_id_context("12345678-1234-1234-1234-123456789012"):
            span = tracer.start_span("test")
        
        # Trace ID should be derived from correlation ID
        assert "12345678" in span.context.trace_id
    
    def test_tracer_sampling(self):
        """Tracer should respect sample rate."""
        tracer = Tracer(service_name="test-service", sample_rate=0.0)
        
        span = tracer.start_span("test")
        
        assert span.context.sampled is False
    
    def test_tracer_error_handling(self):
        """Tracer should handle errors in spans."""
        tracer = Tracer(service_name="test-service")
        
        with pytest.raises(ValueError):
            with tracer.span("test") as span:
                raise ValueError("Test error")
        
        assert span.status == "ERROR"
        assert "Test error" in span.status_message


class TestTracingHelpers:
    """Tests for tracing helper functions."""
    
    def test_trace_span_function(self):
        """trace_span should create spans."""
        with trace_span("test-operation") as span:
            span.set_attribute("key", "value")
        
        assert span.name == "test-operation"
        assert span.end_time is not None
    
    def test_traced_decorator_sync(self):
        """traced decorator should work with sync functions."""
        @traced(name="sync-operation")
        def sync_func():
            return "result"
        
        result = sync_func()
        assert result == "result"
    
    @pytest.mark.asyncio
    async def test_traced_decorator_async(self):
        """traced decorator should work with async functions."""
        @traced(name="async-operation")
        async def async_func():
            return "async-result"
        
        result = await async_func()
        assert result == "async-result"


class TestTracingMiddleware:
    """Tests for tracing middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test application with tracing middleware."""
        async def homepage(request):
            return JSONResponse({"status": "ok"})
        
        async def error_endpoint(request):
            raise ValueError("Test error")
        
        app = Starlette(routes=[
            Route("/", homepage),
            Route("/error", error_endpoint),
        ])
        app.add_middleware(TracingMiddleware)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app, raise_server_exceptions=False)
    
    def test_middleware_creates_span(self, client):
        """Middleware should create span for requests."""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_middleware_handles_errors(self, client):
        """Middleware should handle errors gracefully."""
        response = client.get("/error")
        assert response.status_code == 500