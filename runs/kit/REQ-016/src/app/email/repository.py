"""
Email notification repository.

REQ-016: Email worker service
"""

import logging
from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EmailNotificationRecord:
    """Email notification database record."""
    
    def __init__(
        self,
        id: UUID,
        event_id: UUID,
        contact_id: UUID,
        campaign_id: UUID,
        template_id: UUID,
        to_email: str,
        status: str,
        provider_message_id: Optional[str],
        error_message: Optional[str],
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.event_id = event_id
        self.contact_id = contact_id
        self.campaign_id = campaign_id
        self.template_id = template_id
        self.to_email = to_email
        self.status = status
        self.provider_message_id = provider_message_id
        self.error_message = error_message
        self.created_at = created_at
        self.updated_at = updated_at


class EmailTemplateRecord:
    """Email template database record."""
    
    def __init__(
        self,
        id: UUID,
        name: str,
        type: str,
        subject: str,
        body_html: str,
        body_text: Optional[str],
        locale: str,
    ):
        self.id = id
        self.name = name
        self.type = type
        self.subject = subject
        self.body_html = body_html
        self.body_text = body_text
        self.locale = locale


class ContactRecord:
    """Contact database record (partial)."""
    
    def __init__(
        self,
        id: UUID,
        email: Optional[str],
        preferred_language: str,
    ):
        self.id = id
        self.email = email
        self.preferred_language = preferred_language


class CampaignRecord:
    """Campaign database record (partial for email)."""
    
    def __init__(
        self,
        id: UUID,
        name: str,
        language: str,
        email_completed_template_id: Optional[UUID],
        email_refused_template_id: Optional[UUID],
        email_not_reached_template_id: Optional[UUID],
    ):
        self.id = id
        self.name = name
        self.language = language
        self.email_completed_template_id = email_completed_template_id
        self.email_refused_template_id = email_refused_template_id
        self.email_not_reached_template_id = email_not_reached_template_id


class EmailRepository(Protocol):
    """Repository interface for email operations."""
    
    async def get_template(self, template_id: UUID) -> Optional[EmailTemplateRecord]:
        """Get email template by ID."""
        ...
    
    async def get_contact(self, contact_id: UUID) -> Optional[ContactRecord]:
        """Get contact by ID."""
        ...
    
    async def get_campaign(self, campaign_id: UUID) -> Optional[CampaignRecord]:
        """Get campaign by ID."""
        ...
    
    async def create_notification(
        self,
        event_id: UUID,
        contact_id: UUID,
        campaign_id: UUID,
        template_id: UUID,
        to_email: str,
        status: str,
    ) -> EmailNotificationRecord:
        """Create email notification record."""
        ...
    
    async def update_notification_status(
        self,
        notification_id: UUID,
        status: str,
        provider_message_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update notification status."""
        ...
    
    async def get_notification_by_event(
        self,
        event_id: UUID,
    ) -> Optional[EmailNotificationRecord]:
        """Get notification by event ID for idempotency check."""
        ...


class SQLAlchemyEmailRepository:
    """SQLAlchemy implementation of email repository."""
    
    def __init__(self, session_factory):
        """
        Initialize repository.
        
        Args:
            session_factory: Async session factory.
        """
        self._session_factory = session_factory
    
    async def get_template(self, template_id: UUID) -> Optional[EmailTemplateRecord]:
        """Get email template by ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                select("*").select_from(
                    "email_templates"
                ).where("id = :id"),
                {"id": str(template_id)},
            )
            row = result.fetchone()
            if not row:
                return None
            return EmailTemplateRecord(
                id=UUID(row.id),
                name=row.name,
                type=row.type,
                subject=row.subject,
                body_html=row.body_html,
                body_text=row.body_text,
                locale=row.locale,
            )
    
    async def get_contact(self, contact_id: UUID) -> Optional[ContactRecord]:
        """Get contact by ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                select("*").select_from(
                    "contacts"
                ).where("id = :id"),
                {"id": str(contact_id)},
            )
            row = result.fetchone()
            if not row:
                return None
            return ContactRecord(
                id=UUID(row.id),
                email=row.email,
                preferred_language=row.preferred_language,
            )
    
    async def get_campaign(self, campaign_id: UUID) -> Optional[CampaignRecord]:
        """Get campaign by ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                select("*").select_from(
                    "campaigns"
                ).where("id = :id"),
                {"id": str(campaign_id)},
            )
            row = result.fetchone()
            if not row:
                return None
            return CampaignRecord(
                id=UUID(row.id),
                name=row.name,
                language=row.language,
                email_completed_template_id=UUID(row.email_completed_template_id) if row.email_completed_template_id else None,
                email_refused_template_id=UUID(row.email_refused_template_id) if row.email_refused_template_id else None,
                email_not_reached_template_id=UUID(row.email_not_reached_template_id) if row.email_not_reached_template_id else None,
            )
    
    async def create_notification(
        self,
        event_id: UUID,
        contact_id: UUID,
        campaign_id: UUID,
        template_id: UUID,
        to_email: str,
        status: str,
    ) -> EmailNotificationRecord:
        """Create email notification record."""
        notification_id = uuid4()
        now = datetime.utcnow()
        
        async with self._session_factory() as session:
            await session.execute(
                """
                INSERT INTO email_notifications 
                (id, event_id, contact_id, campaign_id, template_id, to_email, status, created_at, updated_at)
                VALUES (:id, :event_id, :contact_id, :campaign_id, :template_id, :to_email, :status, :created_at, :updated_at)
                """,
                {
                    "id": str(notification_id),
                    "event_id": str(event_id),
                    "contact_id": str(contact_id),
                    "campaign_id": str(campaign_id),
                    "template_id": str(template_id),
                    "to_email": to_email,
                    "status": status,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await session.commit()
        
        return EmailNotificationRecord(
            id=notification_id,
            event_id=event_id,
            contact_id=contact_id,
            campaign_id=campaign_id,
            template_id=template_id,
            to_email=to_email,
            status=status,
            provider_message_id=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
    
    async def update_notification_status(
        self,
        notification_id: UUID,
        status: str,
        provider_message_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update notification status."""
        async with self._session_factory() as session:
            await session.execute(
                """
                UPDATE email_notifications 
                SET status = :status, 
                    provider_message_id = :provider_message_id,
                    error_message = :error_message,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                {
                    "id": str(notification_id),
                    "status": status,
                    "provider_message_id": provider_message_id,
                    "error_message": error_message,
                    "updated_at": datetime.utcnow(),
                },
            )
            await session.commit()
    
    async def get_notification_by_event(
        self,
        event_id: UUID,
    ) -> Optional[EmailNotificationRecord]:
        """Get notification by event ID for idempotency check."""
        async with self._session_factory() as session:
            result = await session.execute(
                select("*").select_from(
                    "email_notifications"
                ).where("event_id = :event_id"),
                {"event_id": str(event_id)},
            )
            row = result.fetchone()
            if not row:
                return None
            return EmailNotificationRecord(
                id=UUID(row.id),
                event_id=UUID(row.event_id),
                contact_id=UUID(row.contact_id),
                campaign_id=UUID(row.campaign_id),
                template_id=UUID(row.template_id),
                to_email=row.to_email,
                status=row.status,
                provider_message_id=row.provider_message_id,
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )