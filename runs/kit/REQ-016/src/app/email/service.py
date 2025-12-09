"""
Email service for sending templated emails.

REQ-016: Email worker service
"""

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.email.interfaces import EmailProvider, EmailMessage, EmailResult, EmailStatus
from app.email.template_renderer import TemplateRenderer
from app.email.repository import (
    EmailRepository,
    EmailTemplateRecord,
    ContactRecord,
    CampaignRecord,
)
from app.email.sqs_consumer import SurveyEvent

logger = logging.getLogger(__name__)


@dataclass
class EmailContext:
    """Context for email rendering."""
    campaign_name: str
    contact_email: str
    contact_language: str
    answers: Optional[list[str]] = None
    attempts: Optional[int] = None
    
    def to_variables(self) -> dict[str, str]:
        """Convert to template variables."""
        variables = {
            "campaign_name": self.campaign_name,
            "contact_email": self.contact_email,
        }
        if self.answers:
            for i, answer in enumerate(self.answers, 1):
                variables[f"answer_{i}"] = answer
        if self.attempts is not None:
            variables["attempts"] = str(self.attempts)
        return variables


class EmailService:
    """
    Service for processing survey events and sending emails.
    
    Handles template lookup, rendering, and email dispatch.
    """
    
    EVENT_TYPE_TO_TEMPLATE_TYPE = {
        "survey.completed": "completed",
        "survey.refused": "refused",
        "survey.not_reached": "not_reached",
    }
    
    def __init__(
        self,
        repository: EmailRepository,
        provider: EmailProvider,
        renderer: TemplateRenderer,
    ):
        """
        Initialize email service.
        
        Args:
            repository: Email repository for data access.
            provider: Email provider for sending.
            renderer: Template renderer.
        """
        self._repository = repository
        self._provider = provider
        self._renderer = renderer
    
    async def process_event(
        self,
        event: SurveyEvent,
        event_id: UUID,
    ) -> Optional[EmailResult]:
        """
        Process a survey event and send appropriate email.
        
        Args:
            event: Survey event to process.
            event_id: Unique event ID for idempotency.
            
        Returns:
            EmailResult if email was sent, None if no email configured.
        """
        # Check for idempotency - already processed this event?
        existing = await self._repository.get_notification_by_event(event_id)
        if existing:
            logger.info(f"Event {event_id} already processed, skipping")
            return EmailResult(
                success=True,
                provider_message_id=existing.provider_message_id,
            )
        
        # Get campaign and contact
        campaign = await self._repository.get_campaign(event.campaign_id)
        if not campaign:
            logger.warning(f"Campaign {event.campaign_id} not found for event {event_id}")
            return None
        
        contact = await self._repository.get_contact(event.contact_id)
        if not contact:
            logger.warning(f"Contact {event.contact_id} not found for event {event_id}")
            return None
        
        if not contact.email:
            logger.info(f"Contact {event.contact_id} has no email, skipping")
            return None
        
        # Get template ID based on event type
        template_id = self._get_template_id(event.event_type, campaign)
        if not template_id:
            logger.info(f"No template configured for {event.event_type} in campaign {campaign.id}")
            return None
        
        # Get template
        template = await self._repository.get_template(template_id)
        if not template:
            logger.warning(f"Template {template_id} not found")
            return None
        
        # Build context and render
        context = EmailContext(
            campaign_name=campaign.name,
            contact_email=contact.email,
            contact_language=contact.preferred_language or campaign.language,
            answers=event.answers,
            attempts=event.attempts,
        )
        
        rendered = self._renderer.render(
            subject_template=template.subject,
            body_html_template=template.body_html,
            body_text_template=template.body_text,
            variables=context.to_variables(),
        )
        
        # Create notification record
        notification = await self._repository.create_notification(
            event_id=event_id,
            contact_id=event.contact_id,
            campaign_id=event.campaign_id,
            template_id=template_id,
            to_email=contact.email,
            status=EmailStatus.PENDING.value,
        )
        
        # Send email
        message = EmailMessage(
            to_email=contact.email,
            subject=rendered.subject,
            body_html=rendered.body_html,
            body_text=rendered.body_text,
        )
        
        result = await self._provider.send(message)
        
        # Update notification status
        await self._repository.update_notification_status(
            notification_id=notification.id,
            status=EmailStatus.SENT.value if result.success else EmailStatus.FAILED.value,
            provider_message_id=result.provider_message_id,
            error_message=result.error_message,
        )
        
        return result
    
    def _get_template_id(
        self,
        event_type: str,
        campaign: CampaignRecord,
    ) -> Optional[UUID]:
        """Get template ID for event type from campaign."""
        template_type = self.EVENT_TYPE_TO_TEMPLATE_TYPE.get(event_type)
        if not template_type:
            return None
        
        if template_type == "completed":
            return campaign.email_completed_template_id
        elif template_type == "refused":
            return campaign.email_refused_template_id
        elif template_type == "not_reached":
            return campaign.email_not_reached_template_id
        
        return None