"""
Structured JSON logging with correlation ID support.

REQ-021: Observability instrumentation
- All log entries in structured JSON format
- Correlation ID propagated across HTTP, telephony, LLM calls
- Log level configurable via environment variable
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Optional, Dict, Union
import re

from infra.observability.config import get_observability_config, LogLevel
from infra.observability.correlation import get_correlation_id


# PII patterns for redaction
PII_PATTERNS = [
    (re.compile(r'\+?\d{10,15}'), '[PHONE_REDACTED]'),  # Phone numbers
    (re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'), '[EMAIL_REDACTED]'),  # Emails
]


def redact_pii(text: str) -> str:
    """Redact PII from text."""
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class StructuredJsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs log records as JSON with standard fields:
    - timestamp: ISO 8601 UTC timestamp
    - level: Log level name
    - logger: Logger name
    - message: Log message
    - correlation_id: Request correlation ID (if available)
    - caller: File, function, and line number (if enabled)
    - exception: Exception info (if present)
    - extra: Additional context fields
    """
    
    def __init__(
        self,
        include_timestamp: bool = True,
        include_caller: bool = True,
        redact_pii: bool = True,
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_caller = include_caller
        self.redact_pii_enabled = redact_pii
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {}
        
        # Timestamp
        if self.include_timestamp:
            log_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Standard fields
        log_data["level"] = record.levelname
        log_data["logger"] = record.name
        
        # Message with optional PII redaction
        message = record.getMessage()
        if self.redact_pii_enabled:
            message = redact_pii(message)
        log_data["message"] = message
        
        # Correlation ID
        correlation_id = get_correlation_id()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        # Caller info
        if self.include_caller:
            log_data["caller"] = {
                "file": record.filename,
                "function": record.funcName,
                "line": record.lineno,
            }
        
        # Exception info
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            if exc_type is not None:
                log_data["exception"] = {
                    "type": exc_type.__name__,
                    "message": str(exc_value),
                    "traceback": traceback.format_exception(exc_type, exc_value, exc_tb),
                }
        
        # Extra fields (excluding standard LogRecord attributes)
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
            'taskName', 'message',
        }
        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                if self.redact_pii_enabled and isinstance(value, str):
                    value = redact_pii(value)
                extra[key] = value
        
        if extra:
            log_data["extra"] = extra
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class StructuredLogger:
    """
    Wrapper around standard logger with structured logging support.
    
    Provides convenience methods for logging with extra context.
    """
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
    
    @property
    def name(self) -> str:
        """Get logger name."""
        return self._logger.name
    
    def _log(
        self,
        level: int,
        message: str,
        *args: Any,
        exc_info: Any = None,
        **kwargs: Any,
    ) -> None:
        """Internal log method with extra context support."""
        extra = kwargs.pop("extra", {})
        # Merge any remaining kwargs into extra
        extra.update(kwargs)
        self._logger.log(level, message, *args, exc_info=exc_info, extra=extra)
    
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, *args, **kwargs)
    
    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._log(logging.ERROR, message, *args, exc_info=True, **kwargs)
    
    def with_context(self, **context: Any) -> "ContextualLogger":
        """Create a logger with bound context."""
        return ContextualLogger(self, context)


class ContextualLogger:
    """Logger with pre-bound context fields."""
    
    def __init__(self, logger: StructuredLogger, context: Dict[str, Any]):
        self._logger = logger
        self._context = context
    
    def _merge_context(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge bound context with call-time kwargs."""
        merged = dict(self._context)
        merged.update(kwargs)
        return merged
    
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(message, *args, **self._merge_context(kwargs))
    
    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(message, *args, **self._merge_context(kwargs))
    
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(message, *args, **self._merge_context(kwargs))
    
    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(message, *args, **self._merge_context(kwargs))
    
    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.critical(message, *args, **self._merge_context(kwargs))
    
    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(message, *args, **self._merge_context(kwargs))


# Logger cache
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """
    Get or create a structured logger.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        StructuredLogger instance.
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]


def configure_logging(
    level: Optional[Union[str, LogLevel]] = None,
    format_json: Optional[bool] = None,
) -> None:
    """
    Configure the logging system.
    
    Should be called once at application startup.
    
    Args:
        level: Log level (uses config default if not specified).
        format_json: Whether to use JSON format (uses config default if not specified).
    """
    config = get_observability_config().logging
    
    # Determine level
    if level is None:
        log_level = config.level.value
    elif isinstance(level, LogLevel):
        log_level = level.value
    else:
        log_level = level.upper()
    
    # Determine format
    use_json = format_json if format_json is not None else config.format_json
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Set formatter
    if use_json:
        formatter = StructuredJsonFormatter(
            include_timestamp=config.include_timestamp,
            include_caller=config.include_caller,
            redact_pii=config.redact_pii,
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)