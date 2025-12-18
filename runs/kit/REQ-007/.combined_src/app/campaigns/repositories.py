from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.campaigns.models import Campaign


class CampaignRepository(Protocol):
    async def get_by_id(self, campaign_id: UUID) -> Campaign | None: ...
    async def update(self, campaign: Campaign) -> Campaign: ...


class ContactRepository(Protocol):
    async def count_by_campaign(self, campaign_id: UUID) -> int: ...
