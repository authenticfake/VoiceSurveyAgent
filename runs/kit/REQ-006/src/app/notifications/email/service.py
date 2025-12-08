from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.bus.models import SurveyEventMessage, SurveyEventType
from app.infra.db.models import (
    Campaign,
    EmailNotification,
    EmailNotificationStatus,
    EmailTemplate,
    EmailTemplateType,
    Event,
)
from app.notifications.email.models import EmailSendRequest
from app.notifications.email.provider import EmailProvider
from app.notifications.email.rendering import TemplateRenderer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessResult:
    status: str
    notification_id: Optional[UUID]
    details: str


class EmailNotificationProcessor:
    """Handles a single survey event and synchronizes EmailNotification state."""

    _EVENT_TEMPLATE_MAP = {
        SurveyEventType.COMPLETED: ("email_completed_template_id", EmailTemplateType.COMPLETED),
        SurveyEventType.REFUSED: ("email_refused_template_id", EmailTemplateType.REFUSED),
        SurveyEventType.NOT_REACHED: ("email_not_reached_template_id", EmailTemplateType.NOT_REACHED),
    }

    def __init__(
        self,
        session_factory: Callable[[], Session],
        provider: EmailProvider,
        renderer: TemplateRenderer,
    ):
        self._session_factory = session_factory
        self._provider = provider
        self._renderer = renderer

    def process(self, message: SurveyEventMessage) -> ProcessResult:
        with self._session_factory() as session:
            notification = self._get_or_create_notification(session, message)
            if notification.status == EmailNotificationStatus.SENT:
                return ProcessResult(
                    status="skipped",
                    notification_id=notification.id,
                    details="notification_already_sent",
                )

            campaign = session.get(Campaign, message.campaign_id)
            contact = notification.contact
            if not campaign or not contact:
                return ProcessResult(
                    status="skipped",
                    notification_id=notification.id,
                    details="campaign_or_contact_missing",
                )
            if not contact.email:
                logger.info("Contact %s has no email; skipping notification", contact.id)
                return self._mark_failed(
                    session,
                    notification,
                    "missing_contact_email",
                )

            template = self._resolve_template(session, campaign, message.event_type)
            if not template:
                return self._mark_failed(session, notification, "template_not_configured")

            context = self._renderer.build_context(
                message=message,
                campaign_payload={"id": str(campaign.id), "name": campaign.name},
                contact_payload={
                    "id": str(contact.id),
                    "email": contact.email,
                    "external_id": contact.external_contact_id,
                },
                template_subject=template.subject,
            )
            rendered = self._renderer.render(template.body_html, template.body_text, context)
            send_request = EmailSendRequest(
                to=contact.email,
                subject=rendered.subject,
                html_body=rendered.html_body,
                text_body=rendered.text_body,
            )

            result = self._provider.send_email(send_request)
            notification.status = EmailNotificationStatus.SENT
            notification.template = template
            notification.provider_message_id = result.message_id
            notification.error_message = None
            session.commit()
            logger.info(
                "Sent %s notification for event %s (notification_id=%s)",
                message.event_type.value,
                message.event_id,
                notification.id,
            )
            return ProcessResult(status="sent", notification_id=notification.id, details="sent")

    def _get_or_create_notification(
        self, session: Session, message: SurveyEventMessage
    ) -> EmailNotification:
        notification = session.scalar(
            select(EmailNotification).where(EmailNotification.event_id == message.event_id)
        )
        if notification:
            return notification

        event = session.get(Event, message.event_id)
        if not event:
            event = Event(
                id=message.event_id,
                event_type=message.event_type.value,  # type: ignore[assignment]
                campaign_id=message.campaign_id,
                contact_id=message.contact_id,
                call_attempt_id=message.call_attempt_id,
                payload=message.model_dump(),
            )
            session.add(event)
            session.flush()

        notification = EmailNotification(
            event_id=message.event_id,
            contact_id=message.contact_id,
            campaign_id=message.campaign_id,
            to_email=message.email or "",
            status=EmailNotificationStatus.PENDING,
        )
        session.add(notification)
        session.flush()
        return notification

    def _resolve_template(
        self, session: Session, campaign: Campaign, event_type: SurveyEventType
    ) -> Optional[EmailTemplate]:
        attr, expected_type = self._EVENT_TEMPLATE_MAP[event_type]
        template_id = getattr(campaign, attr)
        if not template_id:
            return None
        template = session.get(EmailTemplate, template_id)
        if template and template.type != expected_type:
            logger.warning(
                "Template %s type mismatch: expected %s actual %s",
                template.id,
                expected_type,
                template.type,
            )
            return None
        return template

    def _mark_failed(
        self, session: Session, notification: EmailNotification, details: str
    ) -> ProcessResult:
        notification.status = EmailNotificationStatus.FAILED
        notification.error_message = details
        session.commit()
        logger.info("Email notification %s skipped (%s)", notification.id, details)
        return ProcessResult(status="skipped", notification_id=notification.id, details=details)