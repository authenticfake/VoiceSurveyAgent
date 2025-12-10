"""
Tests for structured logging.

REQ-021: Observability instrumentation
"""

import json
import logging
import pytest
from io import StringIO
from unittest.mock import patch

from infra.observability.logging import (
    configure_logging,
    get_logger,
    StructuredJsonFormatter,
    StructuredLogger,
    redact_pii,
)
from infra.observability.config import LogLevel, LoggingConfig
from infra.observability.correlation import correlation_id_context


class TestPIIRedaction:
    """Tests for PII redaction."""
    
    def test_redact_phone_number(self):
        """Phone numbers should be redacted."""
        text = "Call +14155551234 for support"
        result = redact_pii(text)
        assert "+14155551234" not in result
        assert "[PHONE_REDACTED]" in result
    
    def test_redact_email(self):
        """Email addresses should be redacted."""
        text = "Contact user@example.com for help"
        result = redact_pii(text)
        assert "user@example.com" not in result
        assert "[EMAIL_REDACTED]" in result
    
    def test_redact_multiple_pii(self):
        """Multiple PII items should be redacted."""
        text = "User +14155551234 email test@test.com"
        result = redact_pii(text)
        assert "+14155551234" not in result
        assert "test@test.com" not in result
    
    def test_no_pii_unchanged(self):
        """Text without PII should be unchanged."""
        text = "This is a normal message"
        result = redact_pii(text)
        assert result == text


class TestStructuredJsonFormatter:
    """Tests for JSON formatter."""
    
    def test_format_basic_message(self):
        """Basic log message should be formatted as JSON."""
        formatter = StructuredJsonFormatter(
            include_timestamp=True,
            include_caller=True,
            redact_pii=False,
        )
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data
        assert "caller" in data
    
    def test_format_with_correlation_id(self):
        """Correlation ID should be included when set."""
        formatter = StructuredJsonFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        with correlation_id_context("test-correlation-123"):
            output = formatter.format(record)
            data = json.loads(output)
            assert data["correlation_id"] == "test-correlation-123"
    
    def test_format_with_exception(self):
        """Exception info should be included."""
        formatter = StructuredJsonFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert "Test error" in data["exception"]["message"]
    
    def test_format_with_extra_fields(self):
        """Extra fields should be included."""
        formatter = StructuredJsonFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.user_id = "user-123"
        record.campaign_id = "campaign-456"
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "extra" in data
        assert data["extra"]["user_id"] == "user-123"
        assert data["extra"]["campaign_id"] == "campaign-456"
    
    def test_pii_redaction_in_message(self):
        """PII in message should be redacted."""
        formatter = StructuredJsonFormatter(redact_pii=True)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User phone: +14155551234",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "+14155551234" not in data["message"]
        assert "[PHONE_REDACTED]" in data["message"]


class TestStructuredLogger:
    """Tests for StructuredLogger."""
    
    def test_logger_levels(self):
        """All log levels should work."""
        logger = StructuredLogger("test")
        
        # These should not raise
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    
    def test_logger_with_extra(self):
        """Extra kwargs should be passed to log record."""
        logger = StructuredLogger("test")
        
        with patch.object(logger._logger, 'log') as mock_log:
            logger.info("Test", user_id="123", action="test")
            
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args
            assert call_kwargs[1]["extra"]["user_id"] == "123"
            assert call_kwargs[1]["extra"]["action"] == "test"
    
    def test_contextual_logger(self):
        """Contextual logger should bind context."""
        logger = StructuredLogger("test")
        ctx_logger = logger.with_context(campaign_id="camp-123")
        
        with patch.object(logger._logger, 'log') as mock_log:
            ctx_logger.info("Test", extra_field="value")
            
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args
            assert call_kwargs[1]["extra"]["campaign_id"] == "camp-123"
            assert call_kwargs[1]["extra"]["extra_field"] == "value"


class TestConfigureLogging:
    """Tests for logging configuration."""
    
    def test_configure_with_level(self):
        """Log level should be configurable."""
        configure_logging(level="DEBUG")
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_configure_with_log_level_enum(self):
        """LogLevel enum should work."""
        configure_logging(level=LogLevel.WARNING)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
    
    def test_get_logger_caching(self):
        """get_logger should return cached instances."""
        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")
        
        assert logger1 is logger2
    
    def test_get_logger_different_names(self):
        """Different names should return different loggers."""
        logger1 = get_logger("module.a")
        logger2 = get_logger("module.b")
        
        assert logger1 is not logger2
        assert logger1.name != logger2.name