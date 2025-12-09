"""
Dashboard API router.

REQ-017: Campaign dashboard stats API
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.schemas import CampaignStats, CampaignStatsRequest
from app.dashboard.service import CampaignNotFoundError, DashboardService
from app.shared.auth import CurrentUser, UserRole, get_current_user, require_role
from app.shared.cache import get_cache_client
from app.shared.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["dashboard"])


@router.get(
    "/{campaign_id}/stats",
    response_model=CampaignStats,
    summary="Get campaign statistics",
    description="Returns aggregate metrics for a campaign including contact states, "
    "call outcomes, completion rates, and time series data. "
    "Stats are cached with 60-second TTL for performance.",
)
@require_role(UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER, UserRole.VIEWER)
async def get_campaign_stats(
    campaign_id: UUID,
    include_time_series: bool = Query(
        default=True,
        description="Include hourly and daily time series data",
    ),
    time_series_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Hours of hourly time series to include",
    ),
    time_series_days: int = Query(
        default=30,
        ge=1,
        le=90,
        description="Days of daily time series to include",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CampaignStats:
    """
    Get campaign statistics.

    Returns aggregate metrics including:
    - Contact state distribution (pending, completed, refused, etc.)
    - Call outcome distribution (completed, no_answer, busy, etc.)
    - Completion and conversion rates
    - Call duration statistics
    - Time series data for calls per hour/day

    Stats are cached with 60-second TTL for performance.
    Response time target: under 500ms for campaigns with 10k contacts.
    """
    logger.info(
        f"Getting stats for campaign {campaign_id} by user {current_user.id}",
        extra={"campaign_id": str(campaign_id), "user_id": str(current_user.id)},
    )

    request = CampaignStatsRequest(
        include_time_series=include_time_series,
        time_series_hours=time_series_hours,
        time_series_days=time_series_days,
    )

    cache_client = get_cache_client()
    service = DashboardService(db, cache_client)

    try:
        stats = await service.get_campaign_stats(campaign_id, request)
        return stats
    except CampaignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign not found: {campaign_id}",
        )


@router.post(
    "/{campaign_id}/stats/invalidate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate campaign stats cache",
    description="Force refresh of cached statistics for a campaign. "
    "Admin only endpoint.",
)
@require_role(UserRole.ADMIN)
async def invalidate_campaign_stats_cache(
    campaign_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Invalidate cached statistics for a campaign.

    This forces the next stats request to compute fresh data from the database.
    Admin only endpoint.
    """
    logger.info(
        f"Invalidating stats cache for campaign {campaign_id} by admin {current_user.id}",
        extra={"campaign_id": str(campaign_id), "user_id": str(current_user.id)},
    )

    cache_client = get_cache_client()
    service = DashboardService(db, cache_client)
    await service.invalidate_cache(campaign_id)