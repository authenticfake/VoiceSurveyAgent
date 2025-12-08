from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CampaignStatsResponse(BaseModel):
    campaign_id: UUID
    total_contacts: int
    completed_contacts: int
    refused_contacts: int
    not_reached_contacts: int
    in_progress_contacts: int
    pending_contacts: int
    completion_rate: float
    refusal_rate: float
    not_reached_rate: float
    updated_at: datetime


class PaginationMetadata(BaseModel):
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total: int = Field(..., ge=0)


class ContactSummaryModel(BaseModel):
    contact_id: UUID
    external_contact_id: Optional[str] = None
    phone_number: str
    email: Optional[str] = None
    state: str
    attempts_count: int
    last_outcome: Optional[str] = None
    last_attempt_at: Optional[datetime] = None
    updated_at: datetime


class ContactListResponse(BaseModel):
    items: List[ContactSummaryModel]
    pagination: PaginationMetadata


class ContactListQuery(BaseModel):
    state: Optional[str] = Field(default=None)
    last_outcome: Optional[str] = Field(default=None)
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=25, ge=1, le=250)
    sort: str = Field(default="recent", pattern="^(recent|oldest)$")