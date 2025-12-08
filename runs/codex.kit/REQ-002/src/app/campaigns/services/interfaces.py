from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import List, Mapping, Optional, Protocol, Sequence
from uuid import UUID

from app.campaigns.domain.models import CampaignRecord


@dataclass(frozen=True)
class CampaignFilters:
    status: Optional[str] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None


@dataclass(frozen=True)
class PaginationParams:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class PaginationResult:
    page: int
    page_size: int
    total_items: int

    @property
    def total_pages(self) -> int:
        if self.total_items == 0:
            return 0
        return math.ceil(self.total_items / self.page_size)


@dataclass(frozen=True)
class CampaignListResult:
    items: List[CampaignRecord]
    pagination: PaginationResult


@dataclass(frozen=True)
class ContactStats:
    total_contacts: int
    eligible_contacts: int
    excluded_contacts: int


class ContactStatsProvider(Protocol):
    def get_stats(self, campaign_id: UUID) -> ContactStats:
        ...


class CampaignRepository(Protocol):
    def create(self, data: Mapping[str, object], created_by: UUID) -> CampaignRecord: ...

    def update(self, campaign_id: UUID, data: Mapping[str, object]) -> CampaignRecord: ...

    def update_status(self, campaign_id: UUID, status: str) -> CampaignRecord: ...

    def get(self, campaign_id: UUID) -> Optional[CampaignRecord]: ...

    def list(
        self,
        filters: CampaignFilters,
        pagination: PaginationParams,
    ) -> tuple[Sequence[CampaignRecord], int]: ...