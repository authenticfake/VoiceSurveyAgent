"""
Structured JSON logging configuration.

REQ-002: OIDC authentication integration
"""

import logging

import os
import sys
from contextvars import ContextVar
from typing import Any
import json
from datetime import datetime, timezone
# Configure log level from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

from app.config import get_settings

# Context variable for correlation ID
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

class StructuredFormatter(logging.Formatter):
    """JSON-like structured log formatter."""
    _RESERVED = {
        # standard LogRecord attributes
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # 1) Custom extra_data (from log_with_extra)
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):  # type: ignore[attr-defined]
            log_data.update(record.extra_data)  # type: ignore[attr-defined]

        # 2) Standard logging extra=... fields: include any non-reserved attributes
        for k, v in record.__dict__.items():
            if k in self._RESERVED:
                continue
            if k == "extra_data":
                continue
            # avoid overriding base keys unless you want to
            if k in log_data:
                log_data[f"extra_{k}"] = v
            else:
                log_data[k] = v

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    return logger

class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if present
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def setup_logging() -> None:
    """Configure structured JSON logging."""
    settings = get_settings()

    # Create JSON handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.handlers = [handler]

    # SQLAlchemy noise control:
    # - default: WARNING
    # - opt-in verbose via env SQLALCHEMY_LOG_LEVEL=INFO/DEBUG
    sqlalchemy_level = os.getenv("SQLALCHEMY_LOG_LEVEL", "").strip().upper()
    if not sqlalchemy_level:
        sqlalchemy_level = "WARNING"

    logging.getLogger("sqlalchemy.engine").setLevel(sqlalchemy_level)
    logging.getLogger("sqlalchemy.pool").setLevel(sqlalchemy_level)
    logging.getLogger("sqlalchemy.dialects").setLevel(sqlalchemy_level)
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("python_multipart").setLevel(logging.WARNING)
    logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)




def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **extra: Any,
) -> None:
    """Log a message with extra context data."""
    record = logger.makeRecord(
        logger.name,
        level,
        "",
        0,
        message,
        (),
        None,
    )
    record.extra_data = extra  # type: ignore[attr-defined]
    logger.handle(record)