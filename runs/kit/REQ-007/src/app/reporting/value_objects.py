from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional
from uuid import UUID


@dataclass(frozen=True)
class CampaignStats:
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


@dataclass(frozen=True)
class ContactListFilters:
    state: Optional[str] = None
    last_outcome: Optional[str] = None
    page: int = 1
    page_size: int = 25
    sort_desc: bool = True


@dataclass(frozen=True)
class ContactSummary:
    contact_id: UUID
    external_contact_id: Optional[str]
    phone_number: str
    email: Optional[str]
    state: str
    attempts_count: int
    last_outcome: Optional[str]
    last_attempt_at: Optional[datetime]
    updated_at: datetime


@dataclass(frozen=True)
class PaginatedContacts:
    items: Iterable[ContactSummary]
    total: int
    page: int
    page_size: int