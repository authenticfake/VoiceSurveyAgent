"""
Email worker module.

REQ-016: Email worker service
- Email worker polls SQS queue continuously
- survey.completed triggers completed email if template configured
- Template variables substituted from event payload
- EmailNotification record created with status
- Failed sends retried up to 3 times with backoff
"""

from app.email.interfaces import EmailProvider, EmailMessage, EmailResult
from app.email.service import EmailService
from app.email.worker import EmailWorker
from app.email.template_renderer import TemplateRenderer

__all__ = [
    "EmailProvider",
    "EmailMessage",
    "EmailResult",
    "EmailService",
    "EmailWorker",
    "TemplateRenderer",
]