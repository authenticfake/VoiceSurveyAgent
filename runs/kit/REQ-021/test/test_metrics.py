"""
Tests for Prometheus metrics.

REQ-021: Observability instrumentation
"""

import pytest
import time
from unittest.mock import patch

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from infra.observability.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    get_metrics_registry,
    metrics_endpoint,
    track_request_metrics,
)


class TestCounter:
    """Tests for Counter metric."""
    
    def test_counter_increment(self):
        """Counter should increment correctly."""
        counter = Counter(name="test_counter", help_text="Test counter")
        
        counter.inc()
        assert counter.get() == 1.0
        
        counter.inc(5.0)
        assert counter.get() == 6.0
    
    def test_counter_with_labels(self):
        """Counter should track values per label combination."""
        counter = Counter(
            name="test_counter",
            help_text="Test counter",
            label_names=["method", "status"],
        )
        
        counter.inc(method="GET", status="200")
        counter.inc(method="GET", status="200")
        counter.inc(method="POST", status="201")
        
        assert counter.get(method="GET", status="200") == 2.0
        assert counter.get(method="POST", status="201") == 1.0
        assert counter.get(method="GET", status="404") == 0.0
    
    def test_counter_labeled_instance(self):
        """Labeled counter should work correctly."""
        counter = Counter(
            name="test_counter",
            help_text="Test counter",
            label_names=["endpoint"],
        )
        
        labeled = counter.labels(endpoint="/api/test")
        labeled.inc()
        labeled.inc(2.0)
        
        assert counter.get(endpoint="/api/test") == 3.0
    
    def test_counter_collect(self):
        """Counter should collect in Prometheus format."""
        counter = Counter(name="test_total", help_text="Test total")
        counter.inc(10.0)
        
        lines = counter.collect()
        
        assert "# HELP test_total Test total" in lines
        assert "# TYPE test_total counter" in lines
        assert "test_total 10.0" in lines


class TestGauge:
    """Tests for Gauge metric."""
    
    def test_gauge_set(self):
        """Gauge should set value correctly."""
        gauge = Gauge(name="test_gauge", help_text="Test gauge")
        
        gauge.set(42.0)
        assert gauge.get() == 42.0
        
        gauge.set(0.0)
        assert gauge.get() == 0.0
    
    def test_gauge_inc_dec(self):
        """Gauge should increment and decrement."""
        gauge = Gauge(name="test_gauge", help_text="Test gauge")
        
        gauge.inc()
        assert gauge.get() == 1.0
        
        gauge.inc(5.0)
        assert gauge.get() == 6.0
        
        gauge.dec(2.0)
        assert gauge.get() == 4.0
    
    def test_gauge_with_labels(self):
        """Gauge should track values per label combination."""
        gauge = Gauge(
            name="test_gauge",
            help_text="Test gauge",
            label_names=["type"],
        )
        
        gauge.set(10.0, type="active")
        gauge.set(5.0, type="pending")
        
        assert gauge.get(type="active") == 10.0
        assert gauge.get(type="pending") == 5.0
    
    def test_gauge_collect(self):
        """Gauge should collect in Prometheus format."""
        gauge = Gauge(name="test_gauge", help_text="Test gauge")
        gauge.set(42.0)
        
        lines = gauge.collect()
        
        assert "# HELP test_gauge Test gauge" in lines
        assert "# TYPE test_gauge gauge" in lines
        assert "test_gauge 42.0" in lines


class TestHistogram:
    """Tests for Histogram metric."""
    
    def test_histogram_observe(self):
        """Histogram should observe values correctly."""
        histogram = Histogram(
            name="test_histogram",
            help_text="Test histogram",
            buckets=[0.1, 0.5, 1.0, 5.0],
        )
        
        histogram.observe(0.05)
        histogram.observe(0.3)
        histogram.observe(0.8)
        histogram.observe(3.0)
        histogram.observe(10.0)
        
        lines = histogram.collect()
        output = "\n".join(lines)
        
        assert "test_histogram_bucket" in output
        assert "test_histogram_sum" in output
        assert "test_histogram_count" in output
    
    def test_histogram_timer(self):
        """Histogram timer should measure duration."""
        histogram = Histogram(
            name="test_duration",
            help_text="Test duration",
            buckets=[0.01, 0.1, 1.0],
        )
        
        with histogram.time():
            time.sleep(0.05)
        
        lines = histogram.collect()
        output = "\n".join(lines)
        
        assert "test_duration_count 1" in output
    
    def test_histogram_with_labels(self):
        """Histogram should track values per label combination."""
        histogram = Histogram(
            name="test_histogram",
            help_text="Test histogram",
            label_names=["operation"],
            buckets=[0.1, 1.0],
        )
        
        histogram.observe(0.05, operation="read")
        histogram.observe(0.5, operation="write")
        
        lines = histogram.collect()
        output = "\n".join(lines)
        
        assert 'operation="read"' in output
        assert 'operation="write"' in output


class TestMetricsRegistry:
    """Tests for MetricsRegistry."""
    
    def test_registry_creates_metrics(self):
        """Registry should create metrics correctly."""
        registry = MetricsRegistry(namespace="test")
        
        counter = registry.counter("requests", "Total requests")
        gauge = registry.gauge("active", "Active items")
        histogram = registry.histogram("duration", "Duration")
        
        assert counter.name == "test_requests"
        assert gauge.name == "test_active"
        assert histogram.name == "test_duration"
    
    def test_registry_caches_metrics(self):
        """Registry should return same metric instance."""
        registry = MetricsRegistry(namespace="test")
        
        counter1 = registry.counter("requests", "Total requests")
        counter2 = registry.counter("requests", "Total requests")
        
        assert counter1 is counter2
    
    def test_registry_default_metrics(self):
        """Registry should have default application metrics."""
        registry = MetricsRegistry(namespace="app")
        
        assert hasattr(registry, "http_requests_total")
        assert hasattr(registry, "http_request_duration_seconds")
        assert hasattr(registry, "call_attempts_total")
        assert hasattr(registry, "survey_completions_total")
        assert hasattr(registry, "provider_errors_total")
        assert hasattr(registry, "llm_latency_seconds")
    
    def test_registry_collect(self):
        """Registry should collect all metrics."""
        registry = MetricsRegistry(namespace="test")
        
        counter = registry.counter("requests", "Total requests")
        counter.inc(10.0)
        
        gauge = registry.gauge("active", "Active items")
        gauge.set(5.0)
        
        output = registry.collect()
        
        assert "test_requests" in output
        assert "test_active" in output


class TestMetricsEndpoint:
    """Tests for metrics endpoint."""
    
    @pytest.fixture
    def app(self):
        """Create test application with metrics endpoint."""
        app = Starlette(routes=[
            Route("/metrics", metrics_endpoint),
        ])
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Metrics endpoint should return Prometheus format."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content