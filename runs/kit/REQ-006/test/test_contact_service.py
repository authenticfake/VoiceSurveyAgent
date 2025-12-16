"""
Integration tests for contact service.

REQ-006: Contact CSV upload and parsing
"""

import pytest
from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.campaigns.models import Campaign, CampaignStatus, CampaignLanguage, QuestionType
from app.contacts.models import Contact, ContactState
from app.contacts.service import ContactService
from app.shared.exceptions import NotFoundError, ValidationError


@pytest.fixture
def sample_csv_content() -> bytes:
    """Create sample CSV content for testing."""
    return b"""phone_number,email,external_contact_id,language,has_prior_consent,do_not_call
+14155551234,test1@example.com,EXT001,en,true,false
+14155551235,test2@example.com,EXT002,it,false,false
+14155551236,test3@example.com,EXT003,auto,true,true"""


@pytest.fixture
def mixed_validity_csv() -> bytes:
    """Create CSV with mixed valid/invalid rows."""
    return b"""phone_number,email,external_contact_id
+14155551234,test1@example.com,EXT001
invalid_phone,test2@example.com,EXT002
+14155551235,invalid_email,EXT003
+14155551236,test4@example.com,EXT004
+14155551237,,EXT005"""


@pytest_asyncio.fixture
async def draft_campaign(db_session: AsyncSession, test_user) -> Campaign:
    """Create a draft campaign for testing."""
    campaign = Campaign(
        id=uuid4(),
        name="Test Campaign",
        description="Test Description",
        status=CampaignStatus.DRAFT,
        language=CampaignLanguage.EN,
        intro_script="Test intro script",
        question_1_text="Question 1?",
        question_1_type=QuestionType.FREE_TEXT,
        question_2_text="Question 2?",
        question_2_type=QuestionType.NUMERIC,
        question_3_text="Question 3?",
        question_3_type=QuestionType.SCALE,
        max_attempts=3,
        retry_interval_minutes=60,
        created_by_user_id=test_user.id,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


@pytest_asyncio.fixture
async def running_campaign(db_session: AsyncSession, test_user) -> Campaign:
    """Create a running campaign for testing."""
    campaign = Campaign(
        id=uuid4(),
        name="Running Campaign",
        description="Test Description",
        status=CampaignStatus.RUNNING,
        language=CampaignLanguage.EN,
        intro_script="Test intro script",
        question_1_text="Question 1?",
        question_1_type=QuestionType.FREE_TEXT,
        question_2_text="Question 2?",
        question_2_type=QuestionType.NUMERIC,
        question_3_text="Question 3?",
        question_3_type=QuestionType.SCALE,
        max_attempts=3,
        retry_interval_minutes=60,
        created_by_user_id=test_user.id,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


class TestContactServiceUpload:
    """Tests for CSV upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_valid_csv(
        self,
        db_session: AsyncSession,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
    ):
        """Test uploading a valid CSV file."""
        service = ContactService(session=db_session)

        result = await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=sample_csv_content,
        )

        assert result.accepted_count == 3
        assert result.rejected_count == 0
        assert result.total_rows == 3
        assert len(result.errors) == 0
        assert result.acceptance_rate == 1.0

    @pytest.mark.asyncio
    async def test_upload_mixed_validity_csv(
        self,
        db_session: AsyncSession,
        draft_campaign: Campaign,
        mixed_validity_csv: bytes,
    ):
        """Test uploading CSV with mixed valid/invalid rows."""
        service = ContactService(session=db_session)

        result = await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=mixed_validity_csv,
        )

        assert result.accepted_count == 3
        assert result.rejected_count == 2
        assert result.total_rows == 5
        assert len(result.errors) == 2
        assert result.acceptance_rate == 0.6

    @pytest.mark.asyncio
    async def test_upload_to_nonexistent_campaign(
        self,
        db_session: AsyncSession,
        sample_csv_content: bytes,
    ):
        """Test uploading to a non-existent campaign."""
        service = ContactService(session=db_session)

        with pytest.raises(NotFoundError) as exc_info:
            await service.upload_csv(
                campaign_id=uuid4(),
                content=sample_csv_content,
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_to_non_draft_campaign(
        self,
        db_session: AsyncSession,
        running_campaign: Campaign,
        sample_csv_content: bytes,
    ):
        """Test uploading to a non-draft campaign."""
        service = ContactService(session=db_session)

        with pytest.raises(ValidationError) as exc_info:
            await service.upload_csv(
                campaign_id=running_campaign.id,
                content=sample_csv_content,
            )

        assert "draft" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_duplicate_phone_in_file(
        self,
        db_session: AsyncSession,
        draft_campaign: Campaign,
    ):
        """Test uploading CSV with duplicate phone numbers."""
        csv_content = b"""phone_number,email
+14155551234,test1@example.com
+14155551234,test2@example.com
+14155551235,test3@example.com"""

        service = ContactService(session=db_session)

        result = await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=csv_content,
        )

        assert result.accepted_count == 2
        assert result.rejected_count == 1
        assert any("duplicate" in e.error.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_upload_duplicate_phone_in_campaign(
        self,
        db_session: AsyncSession,
        draft_campaign: Campaign,
    ):
        """Test uploading CSV with phone number already in campaign."""
        # First upload
        csv_content1 = b"""phone_number,email
+14155551234,test1@example.com"""

        service = ContactService(session=db_session)
        await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=csv_content1,
        )

        # Second upload with same phone
        csv_content2 = b"""phone_number,email
+14155551234,test2@example.com
+14155551235,test3@example.com"""

        result = await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=csv_content2,
        )

        assert result.accepted_count == 1
        assert result.rejected_count == 1
        assert any("already exists" in e.error.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_upload_creates_contacts_in_pending_state(
        self,
        db_session: AsyncSession,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
    ):
        """Test that uploaded contacts are created in pending state."""
        service = ContactService(session=db_session)

        await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=sample_csv_content,
        )

        # Verify contacts
        contacts_result = await service.get_contacts(
            campaign_id=draft_campaign.id,
        )

        assert contacts_result.total == 3
        for contact in contacts_result.items:
            assert contact.state == ContactState.PENDING

    @pytest.mark.asyncio
    async def test_upload_95_percent_acceptance(
        self,
        db_session: AsyncSession,
        draft_campaign: Campaign,
    ):
        """Test that 95% acceptance rate is achievable."""
        # Create CSV with 100 rows, 95 valid, 5 invalid
        rows = ["phone_number,email"]
        for i in range(95):
            rows.append(f"+1415555{1000+i:04d},test{i}@example.com")
        for i in range(5):
            rows.append(f"invalid{i},test{95+i}@example.com")

        csv_content = "\n".join(rows).encode("utf-8")

        service = ContactService(session=db_session)

        result = await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=csv_content,
        )

        assert result.acceptance_rate >= 0.95


class TestContactServiceGetContacts:
    """Tests for contact retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_contacts_pagination(
        self,
        db_session: AsyncSession,
        draft_campaign: Campaign,
    ):
        """Test paginated contact retrieval."""
        # Create 25 contacts
        rows = ["phone_number,email"]
        for i in range(25):
            rows.append(f"+1415555{1000+i:04d},test{i}@example.com")
        csv_content = "\n".join(rows).encode("utf-8")

        service = ContactService(session=db_session)
        await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=csv_content,
        )

        # Get first page
        result = await service.get_contacts(
            campaign_id=draft_campaign.id,
            page=1,
            page_size=10,
        )

        assert result.total == 25
        assert len(result.items) == 10
        assert result.page == 1
        assert result.page_size == 10
        assert result.pages == 3

        # Get second page
        result = await service.get_contacts(
            campaign_id=draft_campaign.id,
            page=2,
            page_size=10,
        )

        assert len(result.items) == 10
        assert result.page == 2

        # Get third page
        result = await service.get_contacts(
            campaign_id=draft_campaign.id,
            page=3,
            page_size=10,
        )

        assert len(result.items) == 5
        assert result.page == 3

    @pytest.mark.asyncio
    async def test_get_contacts_state_filter(
        self,
        db_session: AsyncSession,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
    ):
        """Test contact retrieval with state filter."""
        service = ContactService(session=db_session)
        await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=sample_csv_content,
        )

        # All contacts should be pending
        result = await service.get_contacts(
            campaign_id=draft_campaign.id,
            state=ContactState.PENDING,
        )
        assert result.total == 3

        # No completed contacts
        result = await service.get_contacts(
            campaign_id=draft_campaign.id,
            state=ContactState.COMPLETED,
        )
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_get_contacts_nonexistent_campaign(
        self,
        db_session: AsyncSession,
    ):
        """Test getting contacts for non-existent campaign."""
        service = ContactService(session=db_session)

        with pytest.raises(NotFoundError):
            await service.get_contacts(campaign_id=uuid4())


class TestContactServiceGetContact:
    """Tests for single contact retrieval."""

    @pytest.mark.asyncio
    async def test_get_contact_success(
        self,
        db_session: AsyncSession,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
    ):
        """Test getting a single contact."""
        service = ContactService(session=db_session)
        await service.upload_csv(
            campaign_id=draft_campaign.id,
            content=sample_csv_content,
        )

        # Get contacts to find an ID
        contacts = await service.get_contacts(campaign_id=draft_campaign.id)
        contact_id = contacts.items[0].id

        # Get single contact
        contact = await service.get_contact(contact_id)

        assert contact.id == contact_id
        assert contact.campaign_id == draft_campaign.id

    @pytest.mark.asyncio
    async def test_get_contact_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test getting a non-existent contact."""
        service = ContactService(session=db_session)

        with pytest.raises(NotFoundError):
            await service.get_contact(uuid4())