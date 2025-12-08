"""Tests for SQLAlchemy models."""
import uuid
from datetime import datetime, time
from decimal import Decimal

import pytest

from app.shared.models import (
    User, Campaign, Contact, ExclusionListEntry, CallAttempt,
    SurveyResponse, Event, EmailNotification, EmailTemplate,
    ProviderConfig, TranscriptSnippet,
)
from app.shared.models.enums import (
    UserRole, CampaignStatus, LanguageCode, QuestionType,
    ContactState, ContactLanguage, CallOutcome, ExclusionSource,
    EventType, EmailStatus, EmailTemplateType, ProviderType, LLMProvider,
)


class TestUserModel:
    """Tests for User model."""
    
    def test_create_user(self):
        """Test creating a user instance."""
        user = User(
            id=uuid.uuid4(),
            oidc_sub="auth0|123456",
            email="test@example.com",
            name="Test User",
            role=UserRole.CAMPAIGN_MANAGER,
        )
        
        assert user.email == "test@example.com"
        assert user.role == UserRole.CAMPAIGN_MANAGER
        assert user.oidc_sub == "auth0|123456"
    
    def test_user_roles(self):
        """Test all user roles are valid."""
        for role in UserRole:
            user = User(
                id=uuid.uuid4(),
                oidc_sub=f"sub_{role.value}",
                email=f"{role.value}@example.com",
                name=f"{role.value} User",
                role=role,
            )
            assert user.role == role


class TestCampaignModel:
    """Tests for Campaign model."""
    
    def test_create_campaign(self):
        """Test creating a campaign instance."""
        campaign = Campaign(
            id=uuid.uuid4(),
            name="Test Campaign",
            description="A test campaign",
            status=CampaignStatus.DRAFT,
            language=LanguageCode.EN,
            intro_script="Hello, this is a survey.",
            question_1_text="How satisfied are you?",
            question_1_type=QuestionType.SCALE,
            question_2_text="What could we improve?",
            question_2_type=QuestionType.FREE_TEXT,
            question_3_text="Rate from 1-10",
            question_3_type=QuestionType.NUMERIC,
            max_attempts=3,
            retry_interval_minutes=60,
            allowed_call_start_local=time(9, 0),
            allowed_call_end_local=time(20, 0),
        )
        
        assert campaign.name == "Test Campaign"
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.max_attempts == 3
        assert campaign.allowed_call_start_local == time(9, 0)
    
    def test_campaign_status_transitions(self):
        """Test campaign status values."""
        statuses = [
            CampaignStatus.DRAFT,
            CampaignStatus.SCHEDULED,
            CampaignStatus.RUNNING,
            CampaignStatus.PAUSED,
            CampaignStatus.COMPLETED,
            CampaignStatus.CANCELLED,
        ]
        
        for status in statuses:
            campaign = Campaign(
                id=uuid.uuid4(),
                name=f"Campaign {status.value}",
                status=status,
            )
            assert campaign.status == status


class TestContactModel:
    """Tests for Contact model."""
    
    def test_create_contact(self):
        """Test creating a contact instance."""
        contact = Contact(
            id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            external_contact_id="EXT-001",
            phone_number="+14155551234",
            email="contact@example.com",
            preferred_language=ContactLanguage.EN,
            has_prior_consent=True,
            do_not_call=False,
            state=ContactState.PENDING,
            attempts_count=0,
        )
        
        assert contact.phone_number == "+14155551234"
        assert contact.state == ContactState.PENDING
        assert contact.has_prior_consent is True
    
    def test_contact_states(self):
        """Test all contact states."""
        for state in ContactState:
            contact = Contact(
                id=uuid.uuid4(),
                campaign_id=uuid.uuid4(),
                phone_number="+14155551234",
                state=state,
            )
            assert contact.state == state


class TestCallAttemptModel:
    """Tests for CallAttempt model."""
    
    def test_create_call_attempt(self):
        """Test creating a call attempt instance."""
        now = datetime.utcnow()
        call_attempt = CallAttempt(
            id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            attempt_number=1,
            call_id="call_abc123",
            provider_call_id="twilio_xyz789",
            started_at=now,
            outcome=CallOutcome.COMPLETED,
            metadata={"duration": 120},
        )
        
        assert call_attempt.call_id == "call_abc123"
        assert call_attempt.outcome == CallOutcome.COMPLETED
        assert call_attempt.metadata["duration"] == 120
    
    def test_call_outcomes(self):
        """Test all call outcomes."""
        for outcome in CallOutcome:
            call_attempt = CallAttempt(
                id=uuid.uuid4(),
                contact_id=uuid.uuid4(),
                campaign_id=uuid.uuid4(),
                attempt_number=1,
                call_id=f"call_{outcome.value}",
                started_at=datetime.utcnow(),
                outcome=outcome,
            )
            assert call_attempt.outcome == outcome


class TestSurveyResponseModel:
    """Tests for SurveyResponse model."""
    
    def test_create_survey_response(self):
        """Test creating a survey response instance."""
        response = SurveyResponse(
            id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            call_attempt_id=uuid.uuid4(),
            q1_answer="Very satisfied",
            q2_answer="Nothing to improve",
            q3_answer="9",
            q1_confidence=Decimal("0.95"),
            q2_confidence=Decimal("0.88"),
            q3_confidence=Decimal("0.99"),
        )
        
        assert response.q1_answer == "Very satisfied"
        assert response.q1_confidence == Decimal("0.95")


class TestEventModel:
    """Tests for Event model."""
    
    def test_create_event(self):
        """Test creating an event instance."""
        event = Event(
            id=uuid.uuid4(),
            event_type=EventType.SURVEY_COMPLETED,
            campaign_id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            call_attempt_id=uuid.uuid4(),
            payload={"answers": ["a1", "a2", "a3"]},
        )
        
        assert event.event_type == EventType.SURVEY_COMPLETED
        assert event.payload["answers"] == ["a1", "a2", "a3"]
    
    def test_event_types(self):
        """Test all event types."""
        for event_type in EventType:
            event = Event(
                id=uuid.uuid4(),
                event_type=event_type,
                campaign_id=uuid.uuid4(),
                contact_id=uuid.uuid4(),
            )
            assert event.event_type == event_type


class TestEmailTemplateModel:
    """Tests for EmailTemplate model."""
    
    def test_create_email_template(self):
        """Test creating an email template instance."""
        template = EmailTemplate(
            id=uuid.uuid4(),
            name="Thank You Template",
            type=EmailTemplateType.COMPLETED,
            subject="Thank you for your feedback",
            body_html="<h1>Thank you!</h1>",
            body_text="Thank you!",
            locale=LanguageCode.EN,
        )
        
        assert template.name == "Thank You Template"
        assert template.type == EmailTemplateType.COMPLETED


class TestProviderConfigModel:
    """Tests for ProviderConfig model."""
    
    def test_create_provider_config(self):
        """Test creating a provider config instance."""
        config = ProviderConfig(
            id=uuid.uuid4(),
            provider_type=ProviderType.TELEPHONY_API,
            provider_name="twilio",
            outbound_number="+14155550000",
            max_concurrent_calls=10,
            llm_provider=LLMProvider.OPENAI,
            llm_model="gpt-4",
            recording_retention_days=180,
            transcript_retention_days=90,
        )
        
        assert config.provider_name == "twilio"
        assert config.llm_provider == LLMProvider.OPENAI
        assert config.max_concurrent_calls == 10


class TestExclusionListEntryModel:
    """Tests for ExclusionListEntry model."""
    
    def test_create_exclusion_entry(self):
        """Test creating an exclusion list entry."""
        entry = ExclusionListEntry(
            id=uuid.uuid4(),
            phone_number="+14155559999",
            reason="Customer requested removal",
            source=ExclusionSource.API,
        )
        
        assert entry.phone_number == "+14155559999"
        assert entry.source == ExclusionSource.API


class TestTranscriptSnippetModel:
    """Tests for TranscriptSnippet model."""
    
    def test_create_transcript_snippet(self):
        """Test creating a transcript snippet."""
        snippet = TranscriptSnippet(
            id=uuid.uuid4(),
            call_attempt_id=uuid.uuid4(),
            transcript_text="Agent: Hello. Customer: Hi.",
            language=LanguageCode.EN,
        )
        
        assert "Hello" in snippet.transcript_text
        assert snippet.language == LanguageCode.EN