"""
Structured logging configuration.

REQ-011: LLM gateway integration
"""

import logging
import os
import sys
from typing import Any

# Log level from environment
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

class StructuredFormatter(logging.Formatter):
    """JSON-like structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured output."""
        # Base fields
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add any extra attributes
        extra = getattr(record, "__dict__", {})
        for key in ["correlation_id", "model", "latency_ms", "provider", "signals", "attempt", "retry_after", "error", "message_count"]:
            if key in extra and key not in log_data:
                log_data[key] = extra[key]

        # Format as key=value pairs for readability
        parts = [f"{k}={v}" for k, v in log_data.items()]
        return " ".join(parts)

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    return logger