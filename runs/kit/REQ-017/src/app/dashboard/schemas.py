"""
Pydantic schemas for dashboard API.

REQ-017: Campaign dashboard stats API
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ContactStateCounts(BaseModel):
    """Contact state distribution counts."""

    total: int = Field(description="Total number of contacts")
    pending: int = Field(description="Contacts pending first call")
    in_progress: int = Field(description="Contacts currently being called")
    completed: int = Field(description="Contacts who completed the survey")
    refused: int = Field(description="Contacts who refused to participate")
    not_reached: int = Field(description="Contacts who could not be reached after max attempts")
    excluded: int = Field(description="Contacts excluded from calling")


class CallOutcomeCounts(BaseModel):
    """Call attempt outcome distribution."""

    total_attempts: int = Field(description="Total number of call attempts")
    completed: int = Field(description="Calls that completed successfully")
    refused: int = Field(description="Calls where contact refused")
    no_answer: int = Field(description="Calls with no answer")
    busy: int = Field(description="Calls that got busy signal")
    failed: int = Field(description="Calls that failed due to error")


class CompletionRates(BaseModel):
    """Completion and conversion rates."""

    completion_rate: float = Field(
        description="Percentage of contacts who completed survey (completed/total)",
        ge=0.0,
        le=100.0,
    )
    refusal_rate: float = Field(
        description="Percentage of contacts who refused (refused/total)",
        ge=0.0,
        le=100.0,
    )
    not_reached_rate: float = Field(
        description="Percentage of contacts not reached (not_reached/total)",
        ge=0.0,
        le=100.0,
    )
    answer_rate: float = Field(
        description="Percentage of calls answered (answered/total_attempts)",
        ge=0.0,
        le=100.0,
    )


class CallDurationStats(BaseModel):
    """Call duration statistics."""

    average_duration_seconds: Optional[float] = Field(
        description="Average call duration in seconds"
    )
    min_duration_seconds: Optional[float] = Field(
        description="Minimum call duration in seconds"
    )
    max_duration_seconds: Optional[float] = Field(
        description="Maximum call duration in seconds"
    )
    total_duration_seconds: Optional[float] = Field(
        description="Total call duration in seconds"
    )


class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series."""

    timestamp: datetime = Field(description="Start of the time bucket")
    attempts: int = Field(description="Number of call attempts in this period")
    completed: int = Field(description="Number of completed surveys in this period")
    refused: int = Field(description="Number of refusals in this period")
    not_reached: int = Field(description="Number of not reached in this period")


class CampaignStats(BaseModel):
    """Complete campaign statistics response."""

    campaign_id: UUID = Field(description="Campaign identifier")
    campaign_name: str = Field(description="Campaign name")
    campaign_status: str = Field(description="Current campaign status")
    contacts: ContactStateCounts = Field(description="Contact state distribution")
    call_outcomes: CallOutcomeCounts = Field(description="Call outcome distribution")
    rates: CompletionRates = Field(description="Completion and conversion rates")
    duration_stats: CallDurationStats = Field(description="Call duration statistics")
    time_series_hourly: List[TimeSeriesDataPoint] = Field(
        description="Hourly time series for last 24 hours"
    )
    time_series_daily: List[TimeSeriesDataPoint] = Field(
        description="Daily time series for last 30 days"
    )
    generated_at: datetime = Field(description="Timestamp when stats were generated")
    cached: bool = Field(description="Whether stats were served from cache")


class CampaignStatsRequest(BaseModel):
    """Request parameters for stats endpoint."""

    include_time_series: bool = Field(
        default=True,
        description="Whether to include time series data",
    )
    time_series_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours of hourly time series data to include",
    )
    time_series_days: int = Field(
        default=30,
        ge=1,
        le=90,
        description="Days of daily time series data to include",
    )