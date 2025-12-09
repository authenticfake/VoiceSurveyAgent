"""
Email provider interfaces and data types.

REQ-016: Email worker service
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class EmailStatus(str, Enum):
    """Email notification status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass(frozen=True)
class EmailMessage:
    """Email message to be sent."""
    to_email: str
    subject: str
    body_html: str
    body_text: Optional[str] = None
    from_email: Optional[str] = None
    reply_to: Optional[str] = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EmailResult:
    """Result of email send operation."""
    success: bool
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class EmailProvider(ABC):
    """
    Abstract interface for email providers.
    
    Implementations can use SMTP, SES, SendGrid, etc.
    """
    
    @abstractmethod
    async def send(self, message: EmailMessage) -> EmailResult:
        """
        Send an email message.
        
        Args:
            message: The email message to send.
            
        Returns:
            EmailResult with success status and provider details.
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the email provider is healthy.
        
        Returns:
            True if provider is available, False otherwise.
        """
        pass