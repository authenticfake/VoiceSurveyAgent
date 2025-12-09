"""
Email service configuration.

REQ-016: Email worker service
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass(frozen=True)
class EmailConfig:
    """Configuration for email service."""
    
    # SMTP settings
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "localhost"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_username: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_USERNAME"))
    smtp_password: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    smtp_use_tls: bool = field(default_factory=lambda: os.getenv("SMTP_USE_TLS", "true").lower() == "true")
    
    # Default sender
    default_from_email: str = field(default_factory=lambda: os.getenv("EMAIL_FROM", "noreply@example.com"))
    default_from_name: str = field(default_factory=lambda: os.getenv("EMAIL_FROM_NAME", "Voice Survey"))
    
    # Worker settings
    poll_interval_seconds: float = field(default_factory=lambda: float(os.getenv("EMAIL_POLL_INTERVAL", "5.0")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("EMAIL_MAX_RETRIES", "3")))
    retry_base_delay_seconds: float = field(default_factory=lambda: float(os.getenv("EMAIL_RETRY_BASE_DELAY", "1.0")))
    retry_max_delay_seconds: float = field(default_factory=lambda: float(os.getenv("EMAIL_RETRY_MAX_DELAY", "60.0")))
    batch_size: int = field(default_factory=lambda: int(os.getenv("EMAIL_BATCH_SIZE", "10")))
    
    # SQS settings
    sqs_queue_url: Optional[str] = field(default_factory=lambda: os.getenv("SQS_QUEUE_URL"))
    sqs_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "eu-central-1"))
    sqs_visibility_timeout: int = field(default_factory=lambda: int(os.getenv("SQS_VISIBILITY_TIMEOUT", "300")))
    sqs_wait_time_seconds: int = field(default_factory=lambda: int(os.getenv("SQS_WAIT_TIME_SECONDS", "20")))


@dataclass(frozen=True)
class SQSConfig:
    """SQS-specific configuration."""
    queue_url: str
    region: str = "eu-central-1"
    visibility_timeout: int = 300
    wait_time_seconds: int = 20
    max_messages: int = 10
    
    @classmethod
    def from_env(cls) -> "SQSConfig":
        """Create config from environment variables."""
        queue_url = os.getenv("SQS_QUEUE_URL")
        if not queue_url:
            raise ValueError("SQS_QUEUE_URL environment variable is required")
        return cls(
            queue_url=queue_url,
            region=os.getenv("AWS_REGION", "eu-central-1"),
            visibility_timeout=int(os.getenv("SQS_VISIBILITY_TIMEOUT", "300")),
            wait_time_seconds=int(os.getenv("SQS_WAIT_TIME_SECONDS", "20")),
            max_messages=int(os.getenv("SQS_MAX_MESSAGES", "10")),
        )