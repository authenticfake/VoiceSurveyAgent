"""
Tests for SMTP email provider.

REQ-016: Email worker service
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import smtplib

from app.email.smtp_provider import SMTPEmailProvider
from app.email.interfaces import EmailMessage
from app.email.config import EmailConfig


@pytest.fixture
def email_config():
    """Create email config."""
    return EmailConfig(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="user",
        smtp_password="pass",
        smtp_use_tls=True,
        default_from_email="noreply@example.com",
        default_from_name="Test Sender",
    )


@pytest.fixture
def smtp_provider(email_config):
    """Create SMTP provider."""
    return SMTPEmailProvider(email_config)


@pytest.fixture
def sample_message():
    """Create sample email message."""
    return EmailMessage(
        to_email="recipient@example.com",
        subject="Test Subject",
        body_html="<p>Test HTML body</p>",
        body_text="Test plain text body",
    )


class TestSMTPEmailProvider:
    """Tests for SMTPEmailProvider."""
    
    @pytest.mark.asyncio
    async def test_send_success(self, smtp_provider, sample_message):
        """Test successful email send."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            
            result = await smtp_provider.send(sample_message)
            
            assert result.success is True
            assert result.provider_message_id is not None
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("user", "pass")
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_smtp_error(self, smtp_provider, sample_message):
        """Test handling SMTP error."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = smtplib.SMTPException("Connection failed")
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            
            result = await smtp_provider.send(sample_message)
            
            assert result.success is False
            assert "SMTP error" in result.error_message
    
    @pytest.mark.asyncio
    async def test_send_with_custom_from(self, smtp_provider):
        """Test sending with custom from address."""
        message = EmailMessage(
            to_email="recipient@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            from_email="custom@example.com",
        )
        
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            
            result = await smtp_provider.send(message)
            
            assert result.success is True
            # Verify the message was sent with custom from
            call_args = mock_server.send_message.call_args
            sent_msg = call_args[0][0]
            assert sent_msg["From"] == "custom@example.com"
    
    @pytest.mark.asyncio
    async def test_send_without_tls(self, email_config):
        """Test sending without TLS."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=25,
            smtp_username=None,
            smtp_password=None,
            smtp_use_tls=False,
            default_from_email="noreply@example.com",
            default_from_name="Test",
        )
        provider = SMTPEmailProvider(config)
        
        message = EmailMessage(
            to_email="recipient@example.com",
            subject="Test",
            body_html="<p>Test</p>",
        )
        
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            
            result = await provider.send(message)
            
            assert result.success is True
            mock_server.starttls.assert_not_called()
            mock_server.login.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, smtp_provider):
        """Test successful health check."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            
            result = await smtp_provider.health_check()
            
            assert result is True
            mock_server.noop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, smtp_provider):
        """Test failed health check."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("Connection refused")
            
            result = await smtp_provider.health_check()
            
            assert result is False