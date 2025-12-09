"""
Tests for email service.

REQ-016: Email worker service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID
from datetime import datetime

from app.email.service import EmailService, EmailContext
from app.email.interfaces import EmailResult, EmailStatus
from app.email.template_renderer import TemplateRenderer
from app.email.sqs_consumer import SurveyEvent
from app.email.repository import (
    EmailTemplateRecord,
    ContactRecord,
    CampaignRecord,
    EmailNotificationRecord,
)


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    repo = AsyncMock()
    repo.get_notification_by_event = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_provider():
    """Create mock email provider."""
    provider = AsyncMock()
    provider.send = AsyncMock(return_value=EmailResult(success=True, provider_message_id="msg-123"))
    return provider


@pytest.fixture
def renderer():
    """Create template renderer."""
    return TemplateRenderer()


@pytest.fixture
def email_service(mock_repository, mock_provider, renderer):
    """Create email service with mocks."""
    return EmailService(
        repository=mock_repository,
        provider=mock_provider,
        renderer=renderer,
    )


@pytest.fixture
def sample_campaign():
    """Create sample campaign record."""
    return CampaignRecord(
        id=uuid4(),
        name="Test Campaign",
        language="en",
        email_completed_template_id=uuid4(),
        email_refused_template_id=uuid4(),
        email_not_reached_template_id=uuid4(),
    )


@pytest.fixture
def sample_contact():
    """Create sample contact record."""
    return ContactRecord(
        id=uuid4(),
        email="test@example.com",
        preferred_language="en",
    )


@pytest.fixture
def sample_template():
    """Create sample email template."""
    return EmailTemplateRecord(
        id=uuid4(),
        name="Completed Template",
        type="completed",
        subject="Thank you for completing {{campaign_name}}",
        body_html="<p>Dear participant, thank you for completing {{campaign_name}}!</p>",
        body_text="Dear participant, thank you for completing {{campaign_name}}!",
        locale="en",
    )


@pytest.fixture
def sample_event(sample_campaign, sample_contact):
    """Create sample survey event."""
    return SurveyEvent(
        event_type="survey.completed",
        campaign_id=sample_campaign.id,
        contact_id=sample_contact.id,
        call_id="call-123",
        timestamp="2024-01-15T10:00:00Z",
        outcome="completed",
        answers=["Very satisfied", "Great service", "10"],
        attempts=1,
        raw_payload={},
    )


class TestEmailService:
    """Tests for EmailService."""
    
    @pytest.mark.asyncio
    async def test_process_completed_event_sends_email(
        self,
        email_service,
        mock_repository,
        mock_provider,
        sample_campaign,
        sample_contact,
        sample_template,
        sample_event,
    ):
        """Test processing completed event sends email."""
        # Setup
        mock_repository.get_campaign = AsyncMock(return_value=sample_campaign)
        mock_repository.get_contact = AsyncMock(return_value=sample_contact)
        mock_repository.get_template = AsyncMock(return_value=sample_template)
        mock_repository.create_notification = AsyncMock(
            return_value=EmailNotificationRecord(
                id=uuid4(),
                event_id=uuid4(),
                contact_id=sample_contact.id,
                campaign_id=sample_campaign.id,
                template_id=sample_template.id,
                to_email=sample_contact.email,
                status=EmailStatus.PENDING.value,
                provider_message_id=None,
                error_message=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        mock_repository.update_notification_status = AsyncMock()
        
        event_id = uuid4()
        
        # Execute
        result = await email_service.process_event(sample_event, event_id)
        
        # Verify
        assert result is not None
        assert result.success is True
        mock_provider.send.assert_called_once()
        mock_repository.create_notification.assert_called_once()
        mock_repository.update_notification_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_event_idempotent(
        self,
        email_service,
        mock_repository,
        sample_event,
    ):
        """Test event processing is idempotent."""
        # Setup - event already processed
        existing_notification = EmailNotificationRecord(
            id=uuid4(),
            event_id=uuid4(),
            contact_id=sample_event.contact_id,
            campaign_id=sample_event.campaign_id,
            template_id=uuid4(),
            to_email="test@example.com",
            status=EmailStatus.SENT.value,
            provider_message_id="existing-msg-id",
            error_message=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.get_notification_by_event = AsyncMock(return_value=existing_notification)
        
        event_id = uuid4()
        
        # Execute
        result = await email_service.process_event(sample_event, event_id)
        
        # Verify - should return success without sending new email
        assert result is not None
        assert result.success is True
        assert result.provider_message_id == "existing-msg-id"
        mock_repository.get_campaign.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_event_no_template_configured(
        self,
        email_service,
        mock_repository,
        sample_contact,
        sample_event,
    ):
        """Test processing event when no template is configured."""
        # Setup - campaign without template
        campaign_no_template = CampaignRecord(
            id=sample_event.campaign_id,
            name="Test Campaign",
            language="en",
            email_completed_template_id=None,  # No template
            email_refused_template_id=None,
            email_not_reached_template_id=None,
        )
        mock_repository.get_campaign = AsyncMock(return_value=campaign_no_template)
        mock_repository.get_contact = AsyncMock(return_value=sample_contact)
        
        event_id = uuid4()
        
        # Execute
        result = await email_service.process_event(sample_event, event_id)
        
        # Verify - should return None (no email to send)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_event_contact_no_email(
        self,
        email_service,
        mock_repository,
        sample_campaign,
        sample_event,
    ):
        """Test processing event when contact has no email."""
        # Setup - contact without email
        contact_no_email = ContactRecord(
            id=sample_event.contact_id,
            email=None,
            preferred_language="en",
        )
        mock_repository.get_campaign = AsyncMock(return_value=sample_campaign)
        mock_repository.get_contact = AsyncMock(return_value=contact_no_email)
        
        event_id = uuid4()
        
        # Execute
        result = await email_service.process_event(sample_event, event_id)
        
        # Verify - should return None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_event_campaign_not_found(
        self,
        email_service,
        mock_repository,
        sample_event,
    ):
        """Test processing event when campaign not found."""
        mock_repository.get_campaign = AsyncMock(return_value=None)
        
        event_id = uuid4()
        
        # Execute
        result = await email_service.process_event(sample_event, event_id)
        
        # Verify
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_refused_event(
        self,
        email_service,
        mock_repository,
        mock_provider,
        sample_campaign,
        sample_contact,
    ):
        """Test processing refused event."""
        # Setup
        refused_template = EmailTemplateRecord(
            id=sample_campaign.email_refused_template_id,
            name="Refused Template",
            type="refused",
            subject="We respect your decision",
            body_html="<p>Thank you for your time.</p>",
            body_text="Thank you for your time.",
            locale="en",
        )
        mock_repository.get_campaign = AsyncMock(return_value=sample_campaign)
        mock_repository.get_contact = AsyncMock(return_value=sample_contact)
        mock_repository.get_template = AsyncMock(return_value=refused_template)
        mock_repository.create_notification = AsyncMock(
            return_value=EmailNotificationRecord(
                id=uuid4(),
                event_id=uuid4(),
                contact_id=sample_contact.id,
                campaign_id=sample_campaign.id,
                template_id=refused_template.id,
                to_email=sample_contact.email,
                status=EmailStatus.PENDING.value,
                provider_message_id=None,
                error_message=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        mock_repository.update_notification_status = AsyncMock()
        
        refused_event = SurveyEvent(
            event_type="survey.refused",
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            call_id="call-456",
            timestamp="2024-01-15T10:00:00Z",
            outcome="refused",
            answers=None,
            attempts=1,
            raw_payload={},
        )
        
        event_id = uuid4()
        
        # Execute
        result = await email_service.process_event(refused_event, event_id)
        
        # Verify
        assert result is not None
        assert result.success is True


class TestEmailContext:
    """Tests for EmailContext."""
    
    def test_to_variables_basic(self):
        """Test basic variable conversion."""
        context = EmailContext(
            campaign_name="Test Survey",
            contact_email="test@example.com",
            contact_language="en",
        )
        
        variables = context.to_variables()
        
        assert variables["campaign_name"] == "Test Survey"
        assert variables["contact_email"] == "test@example.com"
    
    def test_to_variables_with_answers(self):
        """Test variable conversion with answers."""
        context = EmailContext(
            campaign_name="Test Survey",
            contact_email="test@example.com",
            contact_language="en",
            answers=["Answer 1", "Answer 2", "Answer 3"],
        )
        
        variables = context.to_variables()
        
        assert variables["answer_1"] == "Answer 1"
        assert variables["answer_2"] == "Answer 2"
        assert variables["answer_3"] == "Answer 3"
    
    def test_to_variables_with_attempts(self):
        """Test variable conversion with attempts."""
        context = EmailContext(
            campaign_name="Test Survey",
            contact_email="test@example.com",
            contact_language="en",
            attempts=3,
        )
        
        variables = context.to_variables()
        
        assert variables["attempts"] == "3"