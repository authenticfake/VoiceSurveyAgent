"""
Observability configuration.

REQ-021: Observability instrumentation
Centralizes configuration for logging, metrics, and tracing.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""
    level: LogLevel = LogLevel.INFO
    format_json: bool = True
    include_timestamp: bool = True
    include_caller: bool = True
    redact_pii: bool = True
    
    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create config from environment variables."""
        level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        try:
            level = LogLevel(level_str)
        except ValueError:
            level = LogLevel.INFO
        
        return cls(
            level=level,
            format_json=os.getenv("LOG_FORMAT_JSON", "true").lower() == "true",
            include_timestamp=os.getenv("LOG_INCLUDE_TIMESTAMP", "true").lower() == "true",
            include_caller=os.getenv("LOG_INCLUDE_CALLER", "true").lower() == "true",
            redact_pii=os.getenv("LOG_REDACT_PII", "true").lower() == "true",
        )


@dataclass(frozen=True)
class MetricsConfig:
    """Metrics configuration."""
    enabled: bool = True
    endpoint_path: str = "/metrics"
    namespace: str = "voicesurveyagent"
    include_default_metrics: bool = True
    
    @classmethod
    def from_env(cls) -> "MetricsConfig":
        """Create config from environment variables."""
        return cls(
            enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            endpoint_path=os.getenv("METRICS_ENDPOINT", "/metrics"),
            namespace=os.getenv("METRICS_NAMESPACE", "voicesurveyagent"),
            include_default_metrics=os.getenv("METRICS_INCLUDE_DEFAULT", "true").lower() == "true",
        )


@dataclass(frozen=True)
class TracingConfig:
    """Tracing configuration."""
    enabled: bool = True
    service_name: str = "voicesurveyagent"
    otlp_endpoint: Optional[str] = None
    sample_rate: float = 1.0
    propagate_context: bool = True
    
    @classmethod
    def from_env(cls) -> "TracingConfig":
        """Create config from environment variables."""
        sample_rate_str = os.getenv("TRACING_SAMPLE_RATE", "1.0")
        try:
            sample_rate = float(sample_rate_str)
        except ValueError:
            sample_rate = 1.0
        
        return cls(
            enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
            service_name=os.getenv("TRACING_SERVICE_NAME", "voicesurveyagent"),
            otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
            sample_rate=min(max(sample_rate, 0.0), 1.0),
            propagate_context=os.getenv("TRACING_PROPAGATE_CONTEXT", "true").lower() == "true",
        )


@dataclass(frozen=True)
class ObservabilityConfig:
    """Combined observability configuration."""
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    
    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Create config from environment variables."""
        return cls(
            logging=LoggingConfig.from_env(),
            metrics=MetricsConfig.from_env(),
            tracing=TracingConfig.from_env(),
        )


# Global config instance
_config: Optional[ObservabilityConfig] = None


def get_observability_config() -> ObservabilityConfig:
    """Get the global observability configuration."""
    global _config
    if _config is None:
        _config = ObservabilityConfig.from_env()
    return _config


def set_observability_config(config: ObservabilityConfig) -> None:
    """Set the global observability configuration."""
    global _config
    _config = config