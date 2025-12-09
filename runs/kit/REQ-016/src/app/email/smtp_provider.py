"""
SMTP email provider implementation.

REQ-016: Email worker service
"""

import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from uuid import uuid4

from app.email.interfaces import EmailProvider, EmailMessage, EmailResult
from app.email.config import EmailConfig

logger = logging.getLogger(__name__)


class SMTPEmailProvider(EmailProvider):
    """
    SMTP-based email provider.
    
    Supports TLS and authentication.
    """
    
    def __init__(self, config: EmailConfig):
        """
        Initialize SMTP provider.
        
        Args:
            config: Email configuration.
        """
        self._config = config
        self._default_from = f"{config.default_from_name} <{config.default_from_email}>"
    
    async def send(self, message: EmailMessage) -> EmailResult:
        """
        Send email via SMTP.
        
        Args:
            message: Email message to send.
            
        Returns:
            EmailResult with send status.
        """
        try:
            # Run SMTP operations in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._send_sync,
                message,
            )
            return result
        except Exception as e:
            logger.exception(f"Failed to send email to {message.to_email}: {e}")
            return EmailResult(
                success=False,
                error_message=str(e),
            )
    
    def _send_sync(self, message: EmailMessage) -> EmailResult:
        """
        Synchronous SMTP send operation.
        
        Args:
            message: Email message to send.
            
        Returns:
            EmailResult with send status.
        """
        # Build MIME message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = message.from_email or self._default_from
        msg["To"] = message.to_email
        
        if message.reply_to:
            msg["Reply-To"] = message.reply_to
        
        for header_name, header_value in message.headers.items():
            msg[header_name] = header_value
        
        # Add text part first (fallback)
        if message.body_text:
            text_part = MIMEText(message.body_text, "plain", "utf-8")
            msg.attach(text_part)
        
        # Add HTML part
        html_part = MIMEText(message.body_html, "html", "utf-8")
        msg.attach(html_part)
        
        # Generate message ID for tracking
        message_id = f"<{uuid4()}@{self._config.smtp_host}>"
        msg["Message-ID"] = message_id
        
        # Send via SMTP
        try:
            if self._config.smtp_use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port) as server:
                    server.starttls(context=context)
                    if self._config.smtp_username and self._config.smtp_password:
                        server.login(self._config.smtp_username, self._config.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port) as server:
                    if self._config.smtp_username and self._config.smtp_password:
                        server.login(self._config.smtp_username, self._config.smtp_password)
                    server.send_message(msg)
            
            logger.info(f"Email sent successfully to {message.to_email}, message_id={message_id}")
            return EmailResult(
                success=True,
                provider_message_id=message_id,
            )
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending to {message.to_email}: {e}")
            return EmailResult(
                success=False,
                error_message=f"SMTP error: {e}",
            )
    
    async def health_check(self) -> bool:
        """
        Check SMTP server connectivity.
        
        Returns:
            True if server is reachable.
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._health_check_sync)
        except Exception as e:
            logger.warning(f"SMTP health check failed: {e}")
            return False
    
    def _health_check_sync(self) -> bool:
        """Synchronous health check."""
        try:
            with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port, timeout=10) as server:
                server.noop()
            return True
        except Exception:
            return False