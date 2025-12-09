"""
Unit tests for dashboard repository.

REQ-017: Campaign dashboard stats API
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.models import Campaign, Contact
from app.dashboard.repository import DashboardRepository


class TestDashboardRepository:
    """Tests for DashboardRepository."""

    @pytest_asyncio.fixture
    async def repository(self, db_session: AsyncSession):
        """Create repository instance."""
        return DashboardRepository(db_session)

    @pytest.mark.asyncio
    async def test_get_campaign(
        self,
        repository: DashboardRepository,
        test_campaign: Campaign,
    ):
        """Test getting campaign by ID."""
        campaign = await repository.get_campaign(test_campaign.id)
        assert campaign is not None
        assert campaign.id == test_campaign.id
        assert campaign.name == test_campaign.name

    @pytest.mark.asyncio
    async def test_get_contact_state_counts(
        self,
        repository: DashboardRepository,
        test_campaign: Campaign,
        test_contacts: list[Contact],
    ):
        """Test contact state count aggregation."""
        counts = await repository.get_contact_state_counts(test_campaign.id)

        assert counts["total"] == 8
        assert counts["completed"] == 2
        assert counts["refused"] == 1
        assert counts["not_reached"] == 1
        assert counts["pending"] == 2
        assert counts["in_progress"] == 1
        assert counts["excluded"] == 1

    @pytest.mark.asyncio
    async def test_get_call_outcome_counts(
        self,
        repository: DashboardRepository,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
    ):
        """Test call outcome count aggregation."""
        counts = await repository.get_call_outcome_counts(test_campaign.id)

        assert counts["total_attempts"] == 6
        assert counts["completed"] == 2
        assert counts["refused"] == 1
        assert counts["no_answer"] == 3

    @pytest.mark.asyncio
    async def test_get_call_duration_stats(
        self,
        repository: DashboardRepository,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
    ):
        """Test call duration statistics."""
        stats = await repository.get_call_duration_stats(test_campaign.id)

        # We have 3 calls with duration data
        assert stats["average_duration_seconds"] is not None
        assert stats["min_duration_seconds"] is not None
        assert stats["max_duration_seconds"] is not None
        assert stats["total_duration_seconds"] is not None