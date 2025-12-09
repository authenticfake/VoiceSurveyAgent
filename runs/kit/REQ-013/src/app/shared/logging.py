"""
Structured logging utilities.

REQ-013: Dialogue orchestrator Q&A flow
"""

import logging
import sys
from typing import Any


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
        handler.setFormatter(
            logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Log a message with additional context.

    Args:
        logger: Logger instance.
        level: Log level.
        message: Log message.
        **context: Additional context to include.
    """
    extra_info = " ".join(f"{k}={v}" for k, v in context.items())
    full_message = f"{message} {extra_info}" if extra_info else message
    logger.log(level, full_message)