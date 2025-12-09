"""
Unit tests for dashboard schemas.

REQ-017: Campaign dashboard stats API
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.dashboard.schemas import (
    CallDurationStats,
    CallOutcomeCounts,
    CampaignStats,
    CampaignStatsRequest,
    CompletionRates,
    ContactStateCounts,
    TimeSeriesDataPoint,
)


class TestSchemas:
    """Tests for Pydantic schemas."""

    def test_contact_state_counts_valid(self):
        """Test valid ContactStateCounts."""
        counts = ContactStateCounts(
            total=100,
            pending=20,
            in_progress=5,
            completed=50,
            refused=10,
            not_reached=10,
            excluded=5,
        )
        assert counts.total == 100
        assert counts.completed == 50

    def test_completion_rates_bounds(self):
        """Test CompletionRates validates bounds."""
        rates = CompletionRates(
            completion_rate=50.0,
            refusal_rate=10.0,
            not_reached_rate=15.0,
            answer_rate=75.0,
        )
        assert rates.completion_rate == 50.0

        # Test invalid bounds
        with pytest.raises(ValidationError):
            CompletionRates(
                completion_rate=150.0,  # Invalid: > 100
                refusal_rate=10.0,
                not_reached_rate=15.0,
                answer_rate=75.0,
            )

    def test_campaign_stats_request_defaults(self):
        """Test CampaignStatsRequest default values."""
        request = CampaignStatsRequest()
        assert request.include_time_series is True
        assert request.time_series_hours == 24
        assert request.time_series_days == 30

    def test_campaign_stats_request_bounds(self):
        """Test CampaignStatsRequest validates bounds."""
        # Valid bounds
        request = CampaignStatsRequest(
            time_series_hours=168,
            time_series_days=90,
        )
        assert request.time_series_hours == 168

        # Invalid bounds
        with pytest.raises(ValidationError):
            CampaignStatsRequest(time_series_hours=200)

    def test_time_series_data_point(self):
        """Test TimeSeriesDataPoint."""
        point = TimeSeriesDataPoint(
            timestamp=datetime.now(timezone.utc),
            attempts=100,
            completed=50,
            refused=10,
            not_reached=20,
        )
        assert point.attempts == 100

    def test_campaign_stats_full(self):
        """Test full CampaignStats model."""
        stats = CampaignStats(
            campaign_id=uuid4(),
            campaign_name="Test Campaign",
            campaign_status="running",
            contacts=ContactStateCounts(
                total=100,
                pending=20,
                in_progress=5,
                completed=50,
                refused=10,
                not_reached=10,
                excluded=5,
            ),
            call_outcomes=CallOutcomeCounts(
                total_attempts=150,
                completed=50,
                refused=10,
                no_answer=60,
                busy=20,
                failed=10,
            ),
            rates=CompletionRates(
                completion_rate=50.0,
                refusal_rate=10.0,
                not_reached_rate=10.0,
                answer_rate=40.0,
            ),
            duration_stats=CallDurationStats(
                average_duration_seconds=120.5,
                min_duration_seconds=30.0,
                max_duration_seconds=300.0,
                total_duration_seconds=6025.0,
            ),
            time_series_hourly=[],
            time_series_daily=[],
            generated_at=datetime.now(timezone.utc),
            cached=False,
        )
        assert stats.campaign_name == "Test Campaign"
        assert stats.contacts.total == 100