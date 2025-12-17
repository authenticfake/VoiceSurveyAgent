"""
API integration tests for contact router.

REQ-006: Contact CSV upload and parsing
"""

import pytest
from uuid import uuid4

import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.campaigns.models import Campaign, CampaignStatus, CampaignLanguage, QuestionType
from app.main import app
import pytest_asyncio


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


@pytest.fixture
def sample_csv_content() -> bytes:
    """Create sample CSV content for testing."""
    return b"""phone_number,email,external_contact_id,language,has_prior_consent,do_not_call
+14155551234,test1@example.com,EXT001,en,true,false
+14155551235,test2@example.com,EXT002,it,false,false
+14155551236,test3@example.com,EXT003,auto,true,true"""


class TestUploadContactsCSV:
    """Tests for POST /api/campaigns/{id}/contacts/upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_csv_success(
        self,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
        auth_headers: dict[str, str],
    ):
        """Test successful CSV upload."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", sample_csv_content, "text/csv")},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted_count"] == 3
        assert data["rejected_count"] == 0
        assert data["total_rows"] == 3
        assert data["acceptance_rate"] == 1.0
        assert len(data["errors"]) == 0

    @pytest.mark.asyncio
    async def test_upload_csv_with_errors(
        self,
        draft_campaign: Campaign,
        auth_headers: dict[str, str],
    ):
        """Test CSV upload with validation errors."""
        csv_content = b"""phone_number,email
+14155551234,test1@example.com
invalid_phone,test2@example.com
+14155551235,invalid_email"""

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", csv_content, "text/csv")},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted_count"] == 1
        assert data["rejected_count"] == 2
        assert len(data["errors"]) == 2

    @pytest.mark.asyncio
    async def test_upload_csv_campaign_not_found(
        self,
        sample_csv_content: bytes,
        auth_headers: dict[str, str],
    ):
        """Test CSV upload to non-existent campaign."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.post(
                f"/api/campaigns/{uuid4()}/contacts/upload",
                files={"file": ("contacts.csv", sample_csv_content, "text/csv")},
                headers=auth_headers,
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_csv_unauthorized(
        self,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
    ):
        """Test CSV upload without authentication."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", sample_csv_content, "text/csv")},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_csv_viewer_forbidden(
        self,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
        viewer_auth_headers: dict[str, str],
    ):
        """Test CSV upload with viewer role (should be forbidden)."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", sample_csv_content, "text/csv")},
                headers=viewer_auth_headers,
            )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_upload_empty_file(
        self,
        draft_campaign: Campaign,
        auth_headers: dict[str, str],
    ):
        """Test uploading empty file."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", b"", "text/csv")},
                headers=auth_headers,
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_csv_custom_delimiter(
        self,
        draft_campaign: Campaign,
        auth_headers: dict[str, str],
    ):
        """Test CSV upload with custom delimiter."""
        csv_content = b"""phone_number;email
+14155551234;test1@example.com
+14155551235;test2@example.com"""

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", csv_content, "text/csv")},
                params={"delimiter": ";"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted_count"] == 2


class TestListContacts:
    """Tests for GET /api/campaigns/{id}/contacts endpoint."""

    @pytest.mark.asyncio
    async def test_list_contacts_success(
        self,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
        auth_headers: dict[str, str],
    ):
        """Test listing contacts after upload."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            # Upload contacts first
            await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", sample_csv_content, "text/csv")},
                headers=auth_headers,
            )

            # List contacts
            response = await client.get(
                f"/api/campaigns/{draft_campaign.id}/contacts",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_contacts_pagination(
        self,
        draft_campaign: Campaign,
        auth_headers: dict[str, str],
    ):
        """Test contact list pagination."""
        # Create 25 contacts
        rows = ["phone_number,email"]
        for i in range(25):
            rows.append(f"+1415555{1000+i:04d},test{i}@example.com")
        csv_content = "\n".join(rows).encode("utf-8")

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            # Upload contacts
            await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", csv_content, "text/csv")},
                headers=auth_headers,
            )

            # Get first page
            response = await client.get(
                f"/api/campaigns/{draft_campaign.id}/contacts",
                params={"page": 1, "page_size": 10},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["pages"] == 3

    @pytest.mark.asyncio
    async def test_list_contacts_state_filter(
        self,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
        auth_headers: dict[str, str],
    ):
        """Test contact list with state filter."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            # Upload contacts
            await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", sample_csv_content, "text/csv")},
                headers=auth_headers,
            )

            # Filter by pending state
            response = await client.get(
                f"/api/campaigns/{draft_campaign.id}/contacts",
                params={"state": "pending"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_contacts_campaign_not_found(
        self,
        auth_headers: dict[str, str],
    ):
        """Test listing contacts for non-existent campaign."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                f"/api/campaigns/{uuid4()}/contacts",
                headers=auth_headers,
            )

        assert response.status_code == 404


class TestGetContact:
    """Tests for GET /api/campaigns/{id}/contacts/{contact_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_contact_success(
        self,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
        auth_headers: dict[str, str],
    ):
        """Test getting a single contact."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            # Upload contacts
            await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", sample_csv_content, "text/csv")},
                headers=auth_headers,
            )

            # Get contact list to find an ID
            list_response = await client.get(
                f"/api/campaigns/{draft_campaign.id}/contacts",
                headers=auth_headers,
            )
            contact_id = list_response.json()["items"][0]["id"]

            # Get single contact
            response = await client.get(
                f"/api/campaigns/{draft_campaign.id}/contacts/{contact_id}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == contact_id
        assert data["campaign_id"] == str(draft_campaign.id)

    @pytest.mark.asyncio
    async def test_get_contact_not_found(
        self,
        draft_campaign: Campaign,
        auth_headers: dict[str, str],
    ):
        """Test getting a non-existent contact."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                f"/api/campaigns/{draft_campaign.id}/contacts/{uuid4()}",
                headers=auth_headers,
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_contact_wrong_campaign(
        self,
        draft_campaign: Campaign,
        sample_csv_content: bytes,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
        test_user,
    ):
        """Test getting a contact from wrong campaign."""
        # Create another campaign
        other_campaign = Campaign(
            id=uuid4(),
            name="Other Campaign",
            description="Other Description",
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
        db_session.add(other_campaign)
        await db_session.commit()

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost:8080",
        ) as client:
            # Upload contacts to first campaign
            await client.post(
                f"/api/campaigns/{draft_campaign.id}/contacts/upload",
                files={"file": ("contacts.csv", sample_csv_content, "text/csv")},
                headers=auth_headers,
            )

            # Get contact ID from first campaign
            list_response = await client.get(
                f"/api/campaigns/{draft_campaign.id}/contacts",
                headers=auth_headers,
            )
            contact_id = list_response.json()["items"][0]["id"]

            # Try to get contact from other campaign
            response = await client.get(
                f"/api/campaigns/{other_campaign.id}/contacts/{contact_id}",
                headers=auth_headers,
            )

        assert response.status_code == 404