"""
Dashboard statistics service.

REQ-017: Campaign dashboard stats API
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.repository import DashboardRepository
from app.dashboard.schemas import (
    CallDurationStats,
    CallOutcomeCounts,
    CampaignStats,
    CampaignStatsRequest,
    CompletionRates,
    ContactStateCounts,
)
from app.shared.cache import CacheClient
from app.shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CampaignNotFoundError(Exception):
    """Raised when campaign is not found."""

    def __init__(self, campaign_id: UUID):
        self.campaign_id = campaign_id
        super().__init__(f"Campaign not found: {campaign_id}")


class DashboardService:
    """Service for computing and caching campaign statistics."""

    def __init__(
        self,
        session: AsyncSession,
        cache_client: Optional[CacheClient] = None,
    ):
        self._repository = DashboardRepository(session)
        self._cache = cache_client

    def _cache_key(self, campaign_id: UUID) -> str:
        """Generate cache key for campaign stats."""
        return f"campaign_stats:{campaign_id}"

    async def get_campaign_stats(
        self,
        campaign_id: UUID,
        request: Optional[CampaignStatsRequest] = None,
    ) -> CampaignStats:
        """
        Get campaign statistics with caching.

        Args:
            campaign_id: Campaign identifier
            request: Optional request parameters

        Returns:
            CampaignStats with all metrics

        Raises:
            CampaignNotFoundError: If campaign doesn't exist
        """
        if request is None:
            request = CampaignStatsRequest()

        # Try cache first
        cache_key = self._cache_key(campaign_id)
        if self._cache:
            cached = await self._cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for campaign stats: {campaign_id}")
                # Update cached flag and return
                cached["cached"] = True
                return CampaignStats(**cached)

        # Fetch from database
        logger.debug(f"Cache miss for campaign stats: {campaign_id}")
        stats = await self._compute_stats(campaign_id, request)

        # Store in cache
        if self._cache:
            await self._cache.set(
                cache_key,
                stats.model_dump(mode="json"),
                settings.stats_cache_ttl_seconds,
            )

        return stats

    async def _compute_stats(
        self,
        campaign_id: UUID,
        request: CampaignStatsRequest,
    ) -> CampaignStats:
        """Compute fresh statistics from database."""
        # Get campaign
        campaign = await self._repository.get_campaign(campaign_id)
        if campaign is None:
            raise CampaignNotFoundError(campaign_id)

        # Get contact state counts
        contact_counts = await self._repository.get_contact_state_counts(campaign_id)
        contacts = ContactStateCounts(
            total=contact_counts["total"],
            pending=contact_counts.get("pending", 0),
            in_progress=contact_counts.get("in_progress", 0),
            completed=contact_counts.get("completed", 0),
            refused=contact_counts.get("refused", 0),
            not_reached=contact_counts.get("not_reached", 0),
            excluded=contact_counts.get("excluded", 0),
        )

        # Get call outcome counts
        outcome_counts = await self._repository.get_call_outcome_counts(campaign_id)
        call_outcomes = CallOutcomeCounts(
            total_attempts=outcome_counts["total_attempts"],
            completed=outcome_counts.get("completed", 0),
            refused=outcome_counts.get("refused", 0),
            no_answer=outcome_counts.get("no_answer", 0),
            busy=outcome_counts.get("busy", 0),
            failed=outcome_counts.get("failed", 0),
        )

        # Calculate rates
        rates = self._calculate_rates(contacts, call_outcomes)

        # Get duration stats
        duration_data = await self._repository.get_call_duration_stats(campaign_id)
        duration_stats = CallDurationStats(**duration_data)

        # Get time series if requested
        time_series_hourly = []
        time_series_daily = []
        if request.include_time_series:
            time_series_hourly = await self._repository.get_hourly_time_series(
                campaign_id, request.time_series_hours
            )
            time_series_daily = await self._repository.get_daily_time_series(
                campaign_id, request.time_series_days
            )

        return CampaignStats(
            campaign_id=campaign_id,
            campaign_name=campaign.name,
            campaign_status=campaign.status.value,
            contacts=contacts,
            call_outcomes=call_outcomes,
            rates=rates,
            duration_stats=duration_stats,
            time_series_hourly=time_series_hourly,
            time_series_daily=time_series_daily,
            generated_at=datetime.now(timezone.utc),
            cached=False,
        )

    def _calculate_rates(
        self,
        contacts: ContactStateCounts,
        call_outcomes: CallOutcomeCounts,
    ) -> CompletionRates:
        """Calculate completion and conversion rates."""
        # Avoid division by zero
        total_contacts = contacts.total or 1
        total_attempts = call_outcomes.total_attempts or 1

        # Calculate answered calls (completed + refused have been answered)
        answered_calls = call_outcomes.completed + call_outcomes.refused

        return CompletionRates(
            completion_rate=round((contacts.completed / total_contacts) * 100, 2),
            refusal_rate=round((contacts.refused / total_contacts) * 100, 2),
            not_reached_rate=round((contacts.not_reached / total_contacts) * 100, 2),
            answer_rate=round((answered_calls / total_attempts) * 100, 2),
        )

    async def invalidate_cache(self, campaign_id: UUID) -> bool:
        """Invalidate cached stats for a campaign."""
        if self._cache:
            return await self._cache.delete(self._cache_key(campaign_id))
        return False