"""
Prometheus-compatible metrics.

REQ-021: Observability instrumentation
- Prometheus metrics endpoint at /metrics
- Metrics include call_attempts_total, survey_completions_total
- Metrics include provider_errors_total, llm_latency_histogram
"""

import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import threading

from starlette.requests import Request
from starlette.responses import Response


class MetricType(str, Enum):
    """Prometheus metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricLabels:
    """Labels for a metric."""
    labels: Dict[str, str] = field(default_factory=dict)
    
    def key(self) -> str:
        """Generate a unique key for this label combination."""
        if not self.labels:
            return ""
        sorted_items = sorted(self.labels.items())
        return ",".join(f'{k}="{v}"' for k, v in sorted_items)


@dataclass
class Counter:
    """Prometheus counter metric."""
    name: str
    help_text: str
    label_names: List[str] = field(default_factory=list)
    _values: Dict[str, float] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    
    def inc(self, value: float = 1.0, **labels: str) -> None:
        """Increment counter."""
        key = MetricLabels(labels).key()
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value
    
    def get(self, **labels: str) -> float:
        """Get current counter value."""
        key = MetricLabels(labels).key()
        with self._lock:
            return self._values.get(key, 0.0)
    
    def labels(self, **labels: str) -> "LabeledCounter":
        """Return a labeled counter instance."""
        return LabeledCounter(self, labels)
    
    def collect(self) -> List[str]:
        """Collect metric in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            for key, value in self._values.items():
                if key:
                    lines.append(f"{self.name}{{{key}}} {value}")
                else:
                    lines.append(f"{self.name} {value}")
        return lines


@dataclass
class LabeledCounter:
    """Counter with pre-set labels."""
    counter: Counter
    labels: Dict[str, str]
    
    def inc(self, value: float = 1.0) -> None:
        """Increment counter."""
        self.counter.inc(value, **self.labels)


@dataclass
class Gauge:
    """Prometheus gauge metric."""
    name: str
    help_text: str
    label_names: List[str] = field(default_factory=list)
    _values: Dict[str, float] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    
    def set(self, value: float, **labels: str) -> None:
        """Set gauge value."""
        key = MetricLabels(labels).key()
        with self._lock:
            self._values[key] = value
    
    def inc(self, value: float = 1.0, **labels: str) -> None:
        """Increment gauge."""
        key = MetricLabels(labels).key()
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value
    
    def dec(self, value: float = 1.0, **labels: str) -> None:
        """Decrement gauge."""
        key = MetricLabels(labels).key()
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) - value
    
    def get(self, **labels: str) -> float:
        """Get current gauge value."""
        key = MetricLabels(labels).key()
        with self._lock:
            return self._values.get(key, 0.0)
    
    def labels(self, **labels: str) -> "LabeledGauge":
        """Return a labeled gauge instance."""
        return LabeledGauge(self, labels)
    
    def collect(self) -> List[str]:
        """Collect metric in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} gauge",
        ]
        with self._lock:
            for key, value in self._values.items():
                if key:
                    lines.append(f"{self.name}{{{key}}} {value}")
                else:
                    lines.append(f"{self.name} {value}")
        return lines


@dataclass
class LabeledGauge:
    """Gauge with pre-set labels."""
    gauge: Gauge
    labels: Dict[str, str]
    
    def set(self, value: float) -> None:
        """Set gauge value."""
        self.gauge.set(value, **self.labels)
    
    def inc(self, value: float = 1.0) -> None:
        """Increment gauge."""
        self.gauge.inc(value, **self.labels)
    
    def dec(self, value: float = 1.0) -> None:
        """Decrement gauge."""
        self.gauge.dec(value, **self.labels)


@dataclass
class Histogram:
    """Prometheus histogram metric."""
    name: str
    help_text: str
    buckets: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
    label_names: List[str] = field(default_factory=list)
    _bucket_counts: Dict[str, Dict[float, int]] = field(default_factory=dict, repr=False)
    _sums: Dict[str, float] = field(default_factory=dict, repr=False)
    _counts: Dict[str, int] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    
    def observe(self, value: float, **labels: str) -> None:
        """Observe a value."""
        key = MetricLabels(labels).key()
        with self._lock:
            if key not in self._bucket_counts:
                self._bucket_counts[key] = {b: 0 for b in self.buckets}
                self._bucket_counts[key][float('inf')] = 0
                self._sums[key] = 0.0
                self._counts[key] = 0
            
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[key][bucket] += 1
            self._bucket_counts[key][float('inf')] += 1
            self._sums[key] += value
            self._counts[key] += 1
    
    def labels(self, **labels: str) -> "LabeledHistogram":
        """Return a labeled histogram instance."""
        return LabeledHistogram(self, labels)
    
    def time(self) -> "HistogramTimer":
        """Return a timer context manager."""
        return HistogramTimer(self, {})
    
    def collect(self) -> List[str]:
        """Collect metric in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            for key, buckets in self._bucket_counts.items():
                label_str = f"{{{key}," if key else "{"
                cumulative = 0
                for bucket in sorted(b for b in buckets if b != float('inf')):
                    cumulative += buckets[bucket]
                    le_label = f'{label_str}le="{bucket}"}}' if key else f'{{le="{bucket}"}}'
                    lines.append(f"{self.name}_bucket{le_label} {cumulative}")
                
                cumulative += buckets.get(float('inf'), 0) - cumulative
                le_inf = f'{label_str}le="+Inf"}}' if key else '{le="+Inf"}'
                lines.append(f"{self.name}_bucket{le_inf} {self._counts.get(key, 0)}")
                
                suffix = f"{{{key}}}" if key else ""
                lines.append(f"{self.name}_sum{suffix} {self._sums.get(key, 0.0)}")
                lines.append(f"{self.name}_count{suffix} {self._counts.get(key, 0)}")
        return lines


@dataclass
class LabeledHistogram:
    """Histogram with pre-set labels."""
    histogram: Histogram
    labels: Dict[str, str]
    
    def observe(self, value: float) -> None:
        """Observe a value."""
        self.histogram.observe(value, **self.labels)
    
    def time(self) -> "HistogramTimer":
        """Return a timer context manager."""
        return HistogramTimer(self.histogram, self.labels)


class HistogramTimer:
    """Context manager for timing operations."""
    
    def __init__(self, histogram: Histogram, labels: Dict[str, str]):
        self.histogram = histogram
        self.labels = labels
        self.start_time: Optional[float] = None
    
    def __enter__(self) -> "HistogramTimer":
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args: Any) -> None:
        if self.start_time is not None:
            duration = time.perf_counter() - self.start_time
            self.histogram.observe(duration, **self.labels)


class MetricsRegistry:
    """
    Registry for all application metrics.
    
    Provides a central place to define and access metrics.
    """
    
    def __init__(self, namespace: str = "voicesurveyagent"):
        self.namespace = namespace
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
        
        # Pre-define application metrics
        self._init_default_metrics()
    
    def _init_default_metrics(self) -> None:
        """Initialize default application metrics."""
        # HTTP metrics
        self.http_requests_total = self.counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )
        self.http_request_duration_seconds = self.histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )
        
        # Call metrics
        self.call_attempts_total = self.counter(
            "call_attempts_total",
            "Total call attempts",
            ["campaign_id", "outcome"],
        )
        self.survey_completions_total = self.counter(
            "survey_completions_total",
            "Total completed surveys",
            ["campaign_id"],
        )
        self.survey_refusals_total = self.counter(
            "survey_refusals_total",
            "Total refused surveys",
            ["campaign_id"],
        )
        
        # Provider metrics
        self.provider_errors_total = self.counter(
            "provider_errors_total",
            "Total provider errors",
            ["provider", "error_type"],
        )
        self.provider_request_duration_seconds = self.histogram(
            "provider_request_duration_seconds",
            "Provider request duration in seconds",
            ["provider", "operation"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
        
        # LLM metrics
        self.llm_requests_total = self.counter(
            "llm_requests_total",
            "Total LLM requests",
            ["provider", "model"],
        )
        self.llm_errors_total = self.counter(
            "llm_errors_total",
            "Total LLM errors",
            ["provider", "error_type"],
        )
        self.llm_latency_seconds = self.histogram(
            "llm_latency_seconds",
            "LLM request latency in seconds",
            ["provider", "model"],
            buckets=[0.1, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0],
        )
        self.llm_tokens_total = self.counter(
            "llm_tokens_total",
            "Total LLM tokens used",
            ["provider", "model", "type"],
        )
        
        # Email metrics
        self.emails_sent_total = self.counter(
            "emails_sent_total",
            "Total emails sent",
            ["template_type", "status"],
        )
        
        # Active gauges
        self.active_calls = self.gauge(
            "active_calls",
            "Number of currently active calls",
        )
        self.scheduler_queue_size = self.gauge(
            "scheduler_queue_size",
            "Number of contacts pending scheduling",
        )
    
    def _full_name(self, name: str) -> str:
        """Get full metric name with namespace."""
        return f"{self.namespace}_{name}"
    
    def counter(
        self,
        name: str,
        help_text: str,
        label_names: Optional[List[str]] = None,
    ) -> Counter:
        """Create or get a counter metric."""
        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = Counter(
                    name=full_name,
                    help_text=help_text,
                    label_names=label_names or [],
                )
            return self._metrics[full_name]
    
    def gauge(
        self,
        name: str,
        help_text: str,
        label_names: Optional[List[str]] = None,
    ) -> Gauge:
        """Create or get a gauge metric."""
        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = Gauge(
                    name=full_name,
                    help_text=help_text,
                    label_names=label_names or [],
                )
            return self._metrics[full_name]
    
    def histogram(
        self,
        name: str,
        help_text: str,
        label_names: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> Histogram:
        """Create or get a histogram metric."""
        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = Histogram(
                    name=full_name,
                    help_text=help_text,
                    label_names=label_names or [],
                    buckets=buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                )
            return self._metrics[full_name]
    
    def collect(self) -> str:
        """Collect all metrics in Prometheus format."""
        lines = []
        with self._lock:
            for metric in self._metrics.values():
                lines.extend(metric.collect())
                lines.append("")  # Empty line between metrics
        return "\n".join(lines)


# Global registry instance
_registry: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """Get the global metrics registry."""
    global _registry
    if _registry is None:
        from infra.observability.config import get_observability_config
        config = get_observability_config().metrics
        _registry = MetricsRegistry(namespace=config.namespace)
    return _registry


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint handler.
    
    Returns metrics in Prometheus text format.
    """
    registry = get_metrics_registry()
    content = registry.collect()
    return Response(
        content=content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def track_request_metrics(method: str, endpoint: str) -> Callable:
    """
    Decorator to track HTTP request metrics.
    
    Args:
        method: HTTP method.
        endpoint: Endpoint path pattern.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            registry = get_metrics_registry()
            start_time = time.perf_counter()
            status = "500"
            try:
                result = await func(*args, **kwargs)
                if hasattr(result, "status_code"):
                    status = str(result.status_code)
                else:
                    status = "200"
                return result
            except Exception:
                status = "500"
                raise
            finally:
                duration = time.perf_counter() - start_time
                registry.http_requests_total.inc(
                    method=method,
                    endpoint=endpoint,
                    status=status,
                )
                registry.http_request_duration_seconds.observe(
                    duration,
                    method=method,
                    endpoint=endpoint,
                )
        return wrapper
    return decorator