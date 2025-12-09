"""
Structured JSON logging configuration.

REQ-002: OIDC authentication integration
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any
import json
from datetime import datetime, timezone

from app.config import get_settings

# Context variable for correlation ID
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


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

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


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