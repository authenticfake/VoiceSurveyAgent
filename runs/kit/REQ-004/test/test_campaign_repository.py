"""Tests for campaign repository."""

import pytest
from datetime import time
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.shared.database import Base
from app.shared.models.campaign import Campaign
from app.shared.models.user import User
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType, UserRole
from app.campaigns.repository import CampaignRepository


@pytest.fixture
async def async_engine():
    """Create async test engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create async test session."""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def test_user(async_session):
    """Create a test user."""
    user = User(
        id=uuid4(),
        oidc_sub="test-sub",
        email="test@example.com",
        name="Test User",
        role=UserRole.CAMPAIGN_MANAGER,
    )
    async_session.add(user)
    await async_session.commit()
    return user


@pytest.fixture
def repository(async_session):
    """Create repository instance."""
    return CampaignRepository(async_session)


@pytest.fixture
def sample_campaign_data(test_user):
    """Sample campaign data."""
    return {
        "name": "Test Campaign",
        "description": "Test description",
        "status": CampaignStatus.DRAFT,
        "language": LanguageCode.EN,
        "intro_script": "Test intro script for the survey",
        "question_1_text": "Question 1?",
        "question_1_type": QuestionType.FREE_TEXT,
        "question_2_text": "Question 2?",
        "question_2_type": QuestionType.NUMERIC,
        "question_3_text": "Question 3?",
        "question_3_type": QuestionType.SCALE,
        "max_attempts": 3,
        "retry_interval_minutes": 60,
        "allowed_call_start_local": time(9, 0),
        "allowed_call_end_local": time(20, 0),
        "created_by_user_id": test_user.id,
    }


class TestCampaignRepositoryCreate:
    """Tests for campaign creation."""
    
    @pytest.mark.asyncio
    async def test_create_campaign(self, repository, sample_campaign_data, async_session):
        """Test creating a campaign."""
        campaign = Campaign(**sample_campaign_data)
        
        result = await repository.create(campaign)
        
        assert result.id is not None
        assert result.name == "Test Campaign"
        assert result.status == CampaignStatus.DRAFT


class TestCampaignRepositoryGet:
    """Tests for getting campaigns."""
    
    @pytest.mark.asyncio
    async def test_get_by_id_exists(self, repository, sample_campaign_data, async_session):
        """Test getting existing campaign."""
        campaign = Campaign(**sample_campaign_data)
        async_session.add(campaign)
        await async_session.commit()
        
        result = await repository.get_by_id(campaign.id)
        
        assert result is not None
        assert result.id == campaign.id
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_exists(self, repository):
        """Test getting non-existent campaign."""
        result = await repository.get_by_id(uuid4())
        assert result is None


class TestCampaignRepositoryList:
    """Tests for listing campaigns."""
    
    @pytest.mark.asyncio
    async def test_list_campaigns_empty(self, repository):
        """Test listing when no campaigns exist."""
        campaigns, total = await repository.list_campaigns()
        
        assert len(campaigns) == 0
        assert total == 0
    
    @pytest.mark.asyncio
    async def test_list_campaigns_with_data(self, repository, sample_campaign_data, async_session):
        """Test listing with campaigns."""
        for i in range(3):
            data = sample_campaign_data.copy()
            data["name"] = f"Campaign {i}"
            campaign = Campaign(**data)
            async_session.add(campaign)
        await async_session.commit()
        
        campaigns, total = await repository.list_campaigns()
        
        assert len(campaigns) == 3
        assert total == 3
    
    @pytest.mark.asyncio
    async def test_list_campaigns_with_status_filter(self, repository, sample_campaign_data, async_session):
        """Test listing with status filter."""
        # Create campaigns with different statuses
        for status in [CampaignStatus.DRAFT, CampaignStatus.RUNNING, CampaignStatus.DRAFT]:
            data = sample_campaign_data.copy()
            data["status"] = status
            campaign = Campaign(**data)
            async_session.add(campaign)
        await async_session.commit()
        
        campaigns, total = await repository.list_campaigns(status=CampaignStatus.DRAFT)
        
        assert len(campaigns) == 2
        assert total == 2
    
    @pytest.mark.asyncio
    async def test_list_campaigns_pagination(self, repository, sample_campaign_data, async_session):
        """Test pagination."""
        for i in range(5):
            data = sample_campaign_data.copy()
            data["name"] = f"Campaign {i}"
            campaign = Campaign(**data)
            async_session.add(campaign)
        await async_session.commit()
        
        campaigns, total = await repository.list_campaigns(page=1, page_size=2)
        
        assert len(campaigns) == 2
        assert total == 5


class TestCampaignRepositoryUpdate:
    """Tests for updating campaigns."""
    
    @pytest.mark.asyncio
    async def test_update_campaign(self, repository, sample_campaign_data, async_session):
        """Test updating a campaign."""
        campaign = Campaign(**sample_campaign_data)
        async_session.add(campaign)
        await async_session.commit()
        
        campaign.name = "Updated Name"
        result = await repository.update(campaign)
        
        assert result.name == "Updated Name"


class TestCampaignRepositorySoftDelete:
    """Tests for soft deletion."""
    
    @pytest.mark.asyncio
    async def test_soft_delete(self, repository, sample_campaign_data, async_session):
        """Test soft deleting a campaign."""
        campaign = Campaign(**sample_campaign_data)
        async_session.add(campaign)
        await async_session.commit()
        
        result = await repository.soft_delete(campaign)
        
        assert result.status == CampaignStatus.CANCELLED