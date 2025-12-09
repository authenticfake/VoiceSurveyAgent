"""
Pydantic schemas for dashboard and export endpoints.

REQ-017: Campaign dashboard stats API
REQ-018: Campaign CSV export
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.models import ContactState, ExportJobStatus


class CampaignStatsResponse(BaseModel):
    """Campaign statistics response."""

    campaign_id: UUID
    total_contacts: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    refused_count: int = Field(ge=0)
    not_reached_count: int = Field(ge=0)
    pending_count: int = Field(ge=0)
    in_progress_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    completion_rate: float = Field(ge=0.0, le=100.0)
    refusal_rate: float = Field(ge=0.0, le=100.0)
    not_reached_rate: float = Field(ge=0.0, le=100.0)
    average_attempts: float = Field(ge=0.0)
    cached_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TimeSeriesDataPoint(BaseModel):
    """Time series data point for call activity."""

    timestamp: datetime
    calls_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    refused_count: int = Field(ge=0)
    not_reached_count: int = Field(ge=0)


class TimeSeriesResponse(BaseModel):
    """Time series response for call activity."""

    campaign_id: UUID
    granularity: str = Field(description="hour or day")
    data: list[TimeSeriesDataPoint]


class ExportJobResponse(BaseModel):
    """Export job response."""

    id: UUID
    campaign_id: UUID
    status: ExportJobStatus
    download_url: Optional[str] = None
    url_expires_at: Optional[datetime] = None
    total_records: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ExportJobCreateResponse(BaseModel):
    """Response when creating an export job."""

    job_id: UUID
    status: ExportJobStatus
    message: str


class ContactExportRow(BaseModel):
    """Single row in the CSV export."""

    campaign_id: UUID
    contact_id: UUID
    external_contact_id: Optional[str] = None
    phone_number: str
    outcome: ContactState
    attempt_count: int
    last_attempt_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    q1_answer: Optional[str] = None
    q2_answer: Optional[str] = None
    q3_answer: Optional[str] = None

    model_config = {"from_attributes": True}