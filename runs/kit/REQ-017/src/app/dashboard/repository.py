"""
Repository for dashboard data access.

REQ-017: Campaign dashboard stats API
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.models import (
    CallAttempt,
    Campaign,
    CampaignStatus,
    Contact,
    ContactOutcome,
    ContactState,
)
from app.dashboard.schemas import TimeSeriesDataPoint

logger = logging.getLogger(__name__)


class DashboardRepository:
    """Repository for dashboard statistics queries."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_campaign(self, campaign_id: UUID) -> Optional[Campaign]:
        """Get campaign by ID."""
        result = await self._session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def get_contact_state_counts(
        self, campaign_id: UUID
    ) -> dict[str, int]:
        """Get contact counts grouped by state."""
        query = (
            select(Contact.state, func.count(Contact.id).label("count"))
            .where(Contact.campaign_id == campaign_id)
            .group_by(Contact.state)
        )
        result = await self._session.execute(query)
        rows = result.all()

        # Initialize all states to 0
        counts = {state.value: 0 for state in ContactState}
        for row in rows:
            counts[row.state.value] = row.count

        # Calculate total
        counts["total"] = sum(counts.values())
        return counts

    async def get_call_outcome_counts(
        self, campaign_id: UUID
    ) -> dict[str, int]:
        """Get call attempt counts grouped by outcome."""
        query = (
            select(CallAttempt.outcome, func.count(CallAttempt.id).label("count"))
            .where(CallAttempt.campaign_id == campaign_id)
            .group_by(CallAttempt.outcome)
        )
        result = await self._session.execute(query)
        rows = result.all()

        # Initialize all outcomes to 0
        counts = {outcome.value: 0 for outcome in ContactOutcome}
        counts["null"] = 0  # For in-progress calls without outcome

        for row in rows:
            if row.outcome is None:
                counts["null"] = row.count
            else:
                counts[row.outcome.value] = row.count

        # Calculate total
        counts["total_attempts"] = sum(counts.values())
        return counts

    async def get_call_duration_stats(
        self, campaign_id: UUID
    ) -> dict[str, Optional[float]]:
        """Get call duration statistics."""
        # Calculate duration from answered_at to ended_at for completed calls
        query = select(
            func.avg(
                func.extract(
                    "epoch",
                    CallAttempt.ended_at - CallAttempt.answered_at,
                )
            ).label("avg_duration"),
            func.min(
                func.extract(
                    "epoch",
                    CallAttempt.ended_at - CallAttempt.answered_at,
                )
            ).label("min_duration"),
            func.max(
                func.extract(
                    "epoch",
                    CallAttempt.ended_at - CallAttempt.answered_at,
                )
            ).label("max_duration"),
            func.sum(
                func.extract(
                    "epoch",
                    CallAttempt.ended_at - CallAttempt.answered_at,
                )
            ).label("total_duration"),
        ).where(
            CallAttempt.campaign_id == campaign_id,
            CallAttempt.answered_at.isnot(None),
            CallAttempt.ended_at.isnot(None),
        )

        result = await self._session.execute(query)
        row = result.one()

        return {
            "average_duration_seconds": float(row.avg_duration) if row.avg_duration else None,
            "min_duration_seconds": float(row.min_duration) if row.min_duration else None,
            "max_duration_seconds": float(row.max_duration) if row.max_duration else None,
            "total_duration_seconds": float(row.total_duration) if row.total_duration else None,
        }

    async def get_hourly_time_series(
        self, campaign_id: UUID, hours: int = 24
    ) -> List[TimeSeriesDataPoint]:
        """Get hourly time series data for call attempts."""
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours)

        # Use date_trunc for hourly bucketing
        query = text("""
            SELECT 
                date_trunc('hour', started_at) as bucket,
                COUNT(*) as attempts,
                COUNT(*) FILTER (WHERE outcome = 'completed') as completed,
                COUNT(*) FILTER (WHERE outcome = 'refused') as refused,
                COUNT(*) FILTER (WHERE outcome IN ('no_answer', 'busy', 'failed')) as not_reached
            FROM call_attempts
            WHERE campaign_id = :campaign_id
              AND started_at >= :start_time
            GROUP BY bucket
            ORDER BY bucket
        """)

        result = await self._session.execute(
            query,
            {"campaign_id": str(campaign_id), "start_time": start_time},
        )
        rows = result.all()

        return [
            TimeSeriesDataPoint(
                timestamp=row.bucket,
                attempts=row.attempts,
                completed=row.completed,
                refused=row.refused,
                not_reached=row.not_reached,
            )
            for row in rows
        ]

    async def get_daily_time_series(
        self, campaign_id: UUID, days: int = 30
    ) -> List[TimeSeriesDataPoint]:
        """Get daily time series data for call attempts."""
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(days=days)

        # Use date_trunc for daily bucketing
        query = text("""
            SELECT 
                date_trunc('day', started_at) as bucket,
                COUNT(*) as attempts,
                COUNT(*) FILTER (WHERE outcome = 'completed') as completed,
                COUNT(*) FILTER (WHERE outcome = 'refused') as refused,
                COUNT(*) FILTER (WHERE outcome IN ('no_answer', 'busy', 'failed')) as not_reached
            FROM call_attempts
            WHERE campaign_id = :campaign_id
              AND started_at >= :start_time
            GROUP BY bucket
            ORDER BY bucket
        """)

        result = await self._session.execute(
            query,
            {"campaign_id": str(campaign_id), "start_time": start_time},
        )
        rows = result.all()

        return [
            TimeSeriesDataPoint(
                timestamp=row.bucket,
                attempts=row.attempts,
                completed=row.completed,
                refused=row.refused,
                not_reached=row.not_reached,
            )
            for row in rows
        ]