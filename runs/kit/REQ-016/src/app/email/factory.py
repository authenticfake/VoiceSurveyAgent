"""
Factory for creating email worker components.

REQ-016: Email worker service
"""

from typing import Callable

from app.email.config import EmailConfig, SQSConfig
from app.email.interfaces import EmailProvider
from app.email.smtp_provider import SMTPEmailProvider
from app.email.sqs_consumer import SQSConsumer
from app.email.template_renderer import TemplateRenderer
from app.email.repository import EmailRepository, SQLAlchemyEmailRepository
from app.email.service import EmailService
from app.email.worker import EmailWorker, RetryPolicy


def create_email_provider(config: EmailConfig) -> EmailProvider:
    """
    Create email provider based on configuration.
    
    Args:
        config: Email configuration.
        
    Returns:
        Configured email provider.
    """
    return SMTPEmailProvider(config)


def create_email_worker(
    email_config: EmailConfig,
    sqs_config: SQSConfig,
    session_factory: Callable,
) -> EmailWorker:
    """
    Create fully configured email worker.
    
    Args:
        email_config: Email service configuration.
        sqs_config: SQS configuration.
        session_factory: Database session factory.
        
    Returns:
        Configured EmailWorker ready to start.
    """
    # Create components
    provider = create_email_provider(email_config)
    renderer = TemplateRenderer()
    repository = SQLAlchemyEmailRepository(session_factory)
    consumer = SQSConsumer(sqs_config)
    
    # Create service
    service = EmailService(
        repository=repository,
        provider=provider,
        renderer=renderer,
    )
    
    # Create retry policy
    retry_policy = RetryPolicy(
        max_retries=email_config.max_retries,
        base_delay=email_config.retry_base_delay_seconds,
        max_delay=email_config.retry_max_delay_seconds,
    )
    
    # Create worker
    return EmailWorker(
        email_service=service,
        sqs_consumer=consumer,
        retry_policy=retry_policy,
    )