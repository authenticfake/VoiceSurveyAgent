"""Tests for Campaign repository database operations."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.campaigns.repository import CampaignRepository
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType
from app.shared.database import Base


@pytest.fixture
async def test_db():
    """Create test database session."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def campaign_repository(test_db):
    """Create campaign repository with test database."""
    return CampaignRepository(test_db)


@pytest.fixture
def sample_campaign_data():
    """Sample campaign data for testing."""
    return {
        "name": "Test Campaign",
        "description": "Test description",
        "status": CampaignStatus.DRAFT,
        "language": LanguageCode.EN,
        "intro_script": "Test intro",
        "question_1_text": "Q1",
        "question_1_type": QuestionType.FREE_TEXT,
        "question_2_text": "Q2",
        "question_2_type": QuestionType.NUMERIC,
        "question_3_text": "Q3",
        "question_3_type": QuestionType.SCALE,
        "max_attempts": 3,
        "retry_interval_minutes": 60,
        "created_by_user_id": uuid4(),
    }


@pytest.mark.asyncio
async def test_create_campaign(campaign_repository, sample_campaign_data):
    """Test creating a campaign in database."""
    campaign = Campaign(**sample_campaign_data)
    
    created = await campaign_repository.create(campaign)
    
    assert created.id is not None
    assert created.name == sample_campaign_data["name"]
    assert created.status == CampaignStatus.DRAFT


@pytest.mark.asyncio
async def test_get_campaign_by_id(campaign_repository, sample_campaign_data):
    """Test retrieving campaign by ID."""
    campaign = Campaign(**sample_campaign_data)
    created = await campaign_repository.create(campaign)
    
    retrieved = await campaign_repository.get_by_id(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == created.name


@pytest.mark.asyncio
async def test_get_campaign_not_found(campaign_repository):
    """Test retrieving non-existent campaign returns None."""
    non_existent_id = uuid4()
    
    result = await campaign_repository.get_by_id(non_existent_id)
    
    assert result is None


@pytest.mark.asyncio
async def test_update_campaign(campaign_repository, sample_campaign_data):
    """Test updating campaign fields."""
    campaign = Campaign(**sample_campaign_data)
    created = await campaign_repository.create(campaign)
    
    updates = {
        "name": "Updated Name",
        "max_attempts": 5,
    }
    
    updated = await campaign_repository.update(created, updates)
    
    assert updated.name == "Updated Name"
    assert updated.max_attempts == 5


@pytest.mark.asyncio
async def test_update_campaign_status(campaign_repository, sample_campaign_data):
    """Test updating campaign status."""
    campaign = Campaign(**sample_campaign_data)
    created = await campaign_repository.create(campaign)
    
    updated = await campaign_repository.update_status(
        created.id,
        CampaignStatus.RUNNING
    )
    
    assert updated is not None
    assert updated.status == CampaignStatus.RUNNING


@pytest.mark.asyncio
async def test_list_campaigns_with_pagination(campaign_repository, sample_campaign_data):
    """Test listing campaigns with pagination."""
    # Create multiple campaigns
    for i in range(5):
        data = sample_campaign_data.copy()
        data["name"] = f"Campaign {i}"
        campaign = Campaign(**data)
        await campaign_repository.create(campaign)
    
    # Get first page
    campaigns, total = await campaign_repository.get_list(
        offset=0,
        limit=2
    )
    
    assert len(campaigns) == 2
    assert total == 5


@pytest.mark.asyncio
async def test_list_campaigns_with_status_filter(campaign_repository, sample_campaign_data):
    """Test listing campaigns filtered by status."""
    # Create campaigns with different statuses
    for status in [CampaignStatus.DRAFT, CampaignStatus.RUNNING, CampaignStatus.DRAFT]:
        data = sample_campaign_data.copy()
        data["status"] = status
        campaign = Campaign(**data)
        await campaign_repository.create(campaign)
    
    # Filter by DRAFT status
    campaigns, total = await campaign_repository.get_list(
        status=CampaignStatus.DRAFT
    )
    
    assert total == 2
    assert all(c.status == CampaignStatus.DRAFT for c in campaigns)


@pytest.mark.asyncio
async def test_soft_delete_campaign(campaign_repository, sample_campaign_data):
    """Test soft deleting campaign sets status to cancelled."""
    campaign = Campaign(**sample_campaign_data)
    created = await campaign_repository.create(campaign)
    
    result = await campaign_repository.delete(created.id)
    
    assert result is True
    
    # Verify status is cancelled
    deleted = await campaign_repository.get_by_id(created.id)
    assert deleted.status == CampaignStatus.CANCELLED