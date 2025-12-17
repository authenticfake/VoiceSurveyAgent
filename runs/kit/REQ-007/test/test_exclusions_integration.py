"""
Integration tests for exclusion list management.

REQ-007: Exclusion list management
"""

import io
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.models import  User
from app.contacts.exclusions.models import ExclusionListEntry, ExclusionSource, ExclusionBase
from app.contacts.exclusions.repository import ExclusionRepository
from app.contacts.exclusions.service import ExclusionService
from app.contacts.models import Contact, ContactState
from app.campaigns.models import Campaign, CampaignStatus, CampaignLanguage, QuestionType
import pytest_asyncio
from app.auth.models import Base
from app.contacts.exclusions.models import ExclusionBase as Base
from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


# Test database URL - use environment variable or default to test database
TEST_DATABASE_URL = "postgresql+asyncpg://afranco:Andrea.1@localhost:5432/voicesurveyagent"


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Create async engine for tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncSession:
    """Create async session for tests."""
    async_session_maker = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session




@pytest_asyncio.fixture
async def setup_database():
    """Set up test database tables."""
    engine = create_async_engine('postgresql+asyncpg://user:password@localhost/dbname', echo=True)
    async with engine.begin() as conn:
        # Creazione tabelle (assicurarsi che siano completate prima di continuare)
        await conn.run_sync(Base.metadata.create_all)
    yield engine  # Restituire l'engine per l'uso nei test

    # Pulizia
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    """Fornisce una sessione separata per ogni test."""
    async_session = sessionmaker(
        setup_database, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session  # Sessione separata per ogni test



@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession, setup_database) -> User:
    """Create a test admin user."""
    user = User(
        id=uuid4(),
        oidc_sub="test|admin001",
        email="admin@test.com",
        name="Test Admin",
        role="admin",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_campaign(async_session: AsyncSession, test_user: User) -> Campaign:
    """Create a test campaign."""
    campaign = Campaign(
        id=uuid4(),
        name="Test Campaign",
        description="Test campaign for exclusion tests",
        status=CampaignStatus.DRAFT,
        language=CampaignLanguage.EN,
        intro_script="Test intro",
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
    async_session.add(campaign)
    await async_session.commit()
    await async_session.refresh(campaign)
    return campaign


class TestExclusionRepository:
    """Integration tests for ExclusionRepository."""

    @pytest.mark.asyncio
    async def test_create_and_get_by_id(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test creating and retrieving exclusion entry."""
        repo = ExclusionRepository(async_session)

        entry = await repo.create(
            phone_number="+14155551234",
            source=ExclusionSource.API,
            reason="Test reason",
        )
        await async_session.commit()

        retrieved = await repo.get_by_id(entry.id)
        assert retrieved is not None
        assert retrieved.phone_number == "+14155551234"
        assert retrieved.source == ExclusionSource.API
        assert retrieved.reason == "Test reason"

    @pytest.mark.asyncio
    async def test_get_by_phone(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test retrieving exclusion entry by phone number."""
        repo = ExclusionRepository(async_session)

        await repo.create(
            phone_number="+14155559999",
            source=ExclusionSource.IMPORT,
        )
        await async_session.commit()

        entry = await repo.get_by_phone("+14155559999")
        assert entry is not None
        assert entry.phone_number == "+14155559999"

        not_found = await repo.get_by_phone("+10000000000")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_exists(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test checking if phone number exists in exclusion list."""
        repo = ExclusionRepository(async_session)

        await repo.create(
            phone_number="+14155558888",
            source=ExclusionSource.API,
        )
        await async_session.commit()

        assert await repo.exists("+14155558888") is True
        assert await repo.exists("+10000000000") is False

    @pytest.mark.asyncio
    async def test_exists_bulk(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test bulk checking phone numbers."""
        repo = ExclusionRepository(async_session)

        await repo.create(phone_number="+14155551111", source=ExclusionSource.API)
        await repo.create(phone_number="+14155552222", source=ExclusionSource.API)
        await async_session.commit()

        excluded = await repo.exists_bulk([
            "+14155551111",
            "+14155552222",
            "+14155553333",
        ])

        assert "+14155551111" in excluded
        assert "+14155552222" in excluded
        assert "+14155553333" not in excluded

    @pytest.mark.asyncio
    async def test_create_bulk_ignores_duplicates(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test bulk create ignores duplicates."""
        repo = ExclusionRepository(async_session)

        # Create initial entry
        await repo.create(phone_number="+14155554444", source=ExclusionSource.API)
        await async_session.commit()

        # Bulk create with duplicate
        entries = [
            ("+14155554444", ExclusionSource.IMPORT, "Duplicate"),
            ("+14155555555", ExclusionSource.IMPORT, "New"),
        ]
        inserted = await repo.create_bulk(entries)
        await async_session.commit()

        assert inserted == 1  # Only the new one

    @pytest.mark.asyncio
    async def test_delete(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test deleting exclusion entry."""
        repo = ExclusionRepository(async_session)

        entry = await repo.create(
            phone_number="+14155556666",
            source=ExclusionSource.API,
        )
        await async_session.commit()

        deleted = await repo.delete(entry.id)
        await async_session.commit()

        assert deleted is True
        assert await repo.get_by_id(entry.id) is None

    @pytest.mark.asyncio
    async def test_list_all_with_pagination(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test listing exclusions with pagination."""
        repo = ExclusionRepository(async_session)

        # Create multiple entries
        for i in range(15):
            await repo.create(
                phone_number=f"+1415555{i:04d}",
                source=ExclusionSource.API,
            )
        await async_session.commit()

        # Get first page
        entries, total = await repo.list_all(page=1, page_size=10)
        assert len(entries) == 10
        assert total == 15

        # Get second page
        entries, total = await repo.list_all(page=2, page_size=10)
        assert len(entries) == 5
        assert total == 15


class TestExclusionService:
    """Integration tests for ExclusionService."""

    @pytest.mark.asyncio
    async def test_import_csv_valid(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test importing valid CSV."""
        service = ExclusionService(async_session)

        csv_content = """phone_number,reason
+14155551001,Customer request
+14155551002,DNC list
+14155551003,"""

        result = await service.import_csv(csv_content)
        await async_session.commit()

        assert result.accepted_count == 3
        assert result.rejected_count == 0
        assert result.duplicate_count == 0

    @pytest.mark.asyncio
    async def test_import_csv_with_errors(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test importing CSV with invalid rows."""
        service = ExclusionService(async_session)

        csv_content = """phone_number,reason
+14155552001,Valid
invalid_phone,Invalid format
,Empty phone
+14155552002,Also valid"""

        result = await service.import_csv(csv_content)
        await async_session.commit()

        assert result.accepted_count == 2
        assert result.rejected_count == 2
        assert len(result.errors) == 2

    @pytest.mark.asyncio
    async def test_import_csv_with_duplicates_in_file(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test importing CSV with duplicate phone numbers in file."""
        service = ExclusionService(async_session)

        csv_content = """phone_number
+14155553001
+14155553001
+14155553002"""

        result = await service.import_csv(csv_content)
        await async_session.commit()

        assert result.accepted_count == 2
        assert result.rejected_count == 1  # Duplicate in file

    @pytest.mark.asyncio
    async def test_import_csv_with_existing_duplicates(
        self, async_session: AsyncSession, setup_database
    ) -> None:
        """Test importing CSV with phone numbers already in database."""
        service = ExclusionService(async_session)

        # First import
        csv_content1 = """phone_number
+14155554001"""
        await service.import_csv(csv_content1)
        await async_session.commit()

        # Second import with same number
        csv_content2 = """phone_number
+14155554001
+14155554002"""
        result = await service.import_csv(csv_content2)
        await async_session.commit()

        assert result.accepted_count == 1  # Only new one
        assert result.duplicate_count == 1  # Existing in DB

    @pytest.mark.asyncio
    async def test_mark_contacts_excluded(
        self,
        async_session: AsyncSession,
        setup_database,
        test_campaign: Campaign,
    ) -> None:
        """Test marking contacts as excluded based on exclusion list."""
        service = ExclusionService(async_session)

        # Create contacts
        contact1 = Contact(
            campaign_id=test_campaign.id,
            phone_number="+14155555001",
            state=ContactState.PENDING,
        )
        contact2 = Contact(
            campaign_id=test_campaign.id,
            phone_number="+14155555002",
            state=ContactState.PENDING,
        )
        contact3 = Contact(
            campaign_id=test_campaign.id,
            phone_number="+14155555003",
            state=ContactState.PENDING,
        )
        async_session.add_all([contact1, contact2, contact3])
        await async_session.commit()

        # Add one phone to exclusion list
        await service.create_exclusion(
            ExclusionCreateRequest(phone_number="+14155555001"),
            source=ExclusionSource.API,
        )
        await async_session.commit()

        # Sync contacts
        count = await service.mark_contacts_excluded(campaign_id=test_campaign.id)
        await async_session.commit()

        assert count == 1

        # Verify contact state
        await async_session.refresh(contact1)
        await async_session.refresh(contact2)

        assert contact1.state == ContactState.EXCLUDED
        assert contact1.do_not_call is True
        assert contact2.state == ContactState.PENDING


class TestExclusionAPI:
    """Integration tests for exclusion API endpoints."""

    @pytest_asyncio.fixture
    def app(self):
        """Create FastAPI app for testing."""
        from fastapi import FastAPI
        from app.contacts.exclusions.router import router
        from app.shared.database import get_db_session
        from app.auth.middleware import get_current_user

        app = FastAPI()
        app.include_router(router)

        return app

    @pytest_asyncio.fixture
    async def client(self, app, async_session: AsyncSession, test_user: User):
        """Create test client with mocked dependencies."""
        from app.shared.database import get_db_session
        from app.auth.middleware import get_current_user, CurrentUser

        async def override_get_db():
            yield async_session

        def override_get_current_user():
            return CurrentUser(
                id=test_user.id,
                email=test_user.email,
                name=test_user.name,
                role=test_user.role,
            )

        app.dependency_overrides[get_db_session] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_create_exclusion_endpoint(
        self, client: AsyncClient, setup_database
    ) -> None:
        """Test POST /api/exclusions endpoint."""
        response = await client.post(
            "/api/exclusions",
            json={
                "phone_number": "+14155556001",
                "reason": "Test exclusion",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["phone_number"] == "+14155556001"
        assert data["reason"] == "Test exclusion"
        assert data["source"] == "api"

    @pytest.mark.asyncio
    async def test_list_exclusions_endpoint(
        self, client: AsyncClient, async_session: AsyncSession, setup_database
    ) -> None:
        """Test GET /api/exclusions endpoint."""
        # Create some entries
        repo = ExclusionRepository(async_session)
        for i in range(5):
            await repo.create(
                phone_number=f"+1415555700{i}",
                source=ExclusionSource.API,
            )
        await async_session.commit()

        response = await client.get("/api/exclusions?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_import_csv_endpoint(
        self, client: AsyncClient, setup_database
    ) -> None:
        """Test POST /api/exclusions/import endpoint."""
        csv_content = b"""phone_number,reason
+14155558001,Test 1
+14155558002,Test 2"""

        response = await client.post(
            "/api/exclusions/import",
            files={"file": ("exclusions.csv", io.BytesIO(csv_content), "text/csv")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted_count"] == 2
        assert data["rejected_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_exclusion_endpoint(
        self, client: AsyncClient, async_session: AsyncSession, setup_database
    ) -> None:
        """Test DELETE /api/exclusions/{id} endpoint."""
        # Create entry
        repo = ExclusionRepository(async_session)
        entry = await repo.create(
            phone_number="+14155559001",
            source=ExclusionSource.API,
        )
        await async_session.commit()

        response = await client.delete(f"/api/exclusions/{entry.id}")

        assert response.status_code == 204

        # Verify deleted
        assert await repo.get_by_id(entry.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_exclusion(
        self, client: AsyncClient, setup_database
    ) -> None:
        """Test DELETE /api/exclusions/{id} with non-existent ID."""
        response = await client.delete(f"/api/exclusions/{uuid4()}")

        assert response.status_code == 404