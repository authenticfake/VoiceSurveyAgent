"""
Unit tests for dashboard service.

REQ-017: Campaign dashboard stats API
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.models import Campaign, Contact
from app.dashboard.schemas import CampaignStatsRequest
from app.dashboard.service import CampaignNotFoundError, DashboardService


class TestDashboardService:
    """Tests for DashboardService."""

    @pytest_asyncio.fixture
    async def service(self, db_session: AsyncSession, mock_cache):
        """Create service instance."""
        return DashboardService(db_session, mock_cache)

    @pytest.mark.asyncio
    async def test_get_campaign_stats_returns_correct_counts(
        self,
        service: DashboardService,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
    ):
        """Test that stats return correct contact state counts."""
        stats = await service.get_campaign_stats(test_campaign.id)

        # Verify contact counts
        assert stats.contacts.total == 8
        assert stats.contacts.completed == 2
        assert stats.contacts.refused == 1
        assert stats.contacts.not_reached == 1
        assert stats.contacts.pending == 2
        assert stats.contacts.in_progress == 1
        assert stats.contacts.excluded == 1

    @pytest.mark.asyncio
    async def test_get_campaign_stats_returns_correct_call_outcomes(
        self,
        service: DashboardService,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
    ):
        """Test that stats return correct call outcome counts."""
        stats = await service.get_campaign_stats(test_campaign.id)

        # Verify call outcome counts
        assert stats.call_outcomes.total_attempts == 6
        assert stats.call_outcomes.completed == 2
        assert stats.call_outcomes.refused == 1
        assert stats.call_outcomes.no_answer == 3
        assert stats.call_outcomes.busy == 0
        assert stats.call_outcomes.failed == 0

    @pytest.mark.asyncio
    async def test_get_campaign_stats_calculates_rates(
        self,
        service: DashboardService,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
    ):
        """Test that completion rates are calculated correctly."""
        stats = await service.get_campaign_stats(test_campaign.id)

        # 2 completed out of 8 total = 25%
        assert stats.rates.completion_rate == 25.0
        # 1 refused out of 8 total = 12.5%
        assert stats.rates.refusal_rate == 12.5
        # 1 not_reached out of 8 total = 12.5%
        assert stats.rates.not_reached_rate == 12.5
        # 3 answered (2 completed + 1 refused) out of 6 attempts = 50%
        assert stats.rates.answer_rate == 50.0

    @pytest.mark.asyncio
    async def test_get_campaign_stats_returns_duration_stats(
        self,
        service: DashboardService,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
    ):
        """Test that duration stats are calculated."""
        stats = await service.get_campaign_stats(test_campaign.id)

        # We have 3 calls with answered_at and ended_at
        # 2 completed calls: ~3 minutes each = 170 seconds
        # 1 refused call: ~20 seconds
        assert stats.duration_stats.average_duration_seconds is not None
        assert stats.duration_stats.min_duration_seconds is not None
        assert stats.duration_stats.max_duration_seconds is not None

    @pytest.mark.asyncio
    async def test_get_campaign_stats_not_found(
        self,
        service: DashboardService,
    ):
        """Test that non-existent campaign raises error."""
        with pytest.raises(CampaignNotFoundError):
            await service.get_campaign_stats(uuid4())

    @pytest.mark.asyncio
    async def test_get_campaign_stats_uses_cache(
        self,
        service: DashboardService,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
        mock_cache,
    ):
        """Test that stats are cached and returned from cache."""
        # First call - should compute and cache
        stats1 = await service.get_campaign_stats(test_campaign.id)
        assert stats1.cached is False

        # Second call - should return from cache
        stats2 = await service.get_campaign_stats(test_campaign.id)
        assert stats2.cached is True

    @pytest.mark.asyncio
    async def test_get_campaign_stats_without_time_series(
        self,
        service: DashboardService,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
    ):
        """Test stats without time series data."""
        request = CampaignStatsRequest(include_time_series=False)
        stats = await service.get_campaign_stats(test_campaign.id, request)

        assert stats.time_series_hourly == []
        assert stats.time_series_daily == []

    @pytest.mark.asyncio
    async def test_invalidate_cache(
        self,
        service: DashboardService,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
    ):
        """Test cache invalidation."""
        # Populate cache
        await service.get_campaign_stats(test_campaign.id)

        # Invalidate
        result = await service.invalidate_cache(test_campaign.id)
        assert result is True

        # Next call should not be cached
        stats = await service.get_campaign_stats(test_campaign.id)
        assert stats.cached is False