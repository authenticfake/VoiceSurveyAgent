# runs/kit/REQ-002/src/app/campaigns/validation.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import Any
from uuid import UUID

from app.campaigns.models import Campaign, CampaignStatus
from app.shared.exceptions import ValidationError


@dataclass(slots=True)
class ValidationResult:
    errors: list[dict[str, str]] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, field: str, message: str) -> None:
        self.errors.append({"field": field, "message": message})


class CampaignValidationService:
    def __init__(self, campaign_repository: Any, contact_repository: Any) -> None:
        self._campaign_repo = campaign_repository
        self._contact_repo = contact_repository

    async def validate_for_activation(self, campaign_id: UUID) -> ValidationResult:
        campaign = await self._campaign_repo.get_by_id(campaign_id)
        if campaign is None:
            raise ValidationError("Campaign not found", details=[{"field": "campaign", "message": "Campaign not found"}])

        result = ValidationResult()

        # Contacts must exist
        contact_count = await self._contact_repo.count_by_campaign(campaign_id)
        if not isinstance(contact_count, int) or contact_count <= 0:
            result.add_error("contacts", "Campaign must have at least one contact")

        # Intro script required
        intro_script = getattr(campaign, "intro_script", None)
        if intro_script is None or not str(intro_script).strip():
            result.add_error("intro_script", "Intro script is required")

        # Questions required
        for idx in (1, 2, 3):
            text = getattr(campaign, f"question_{idx}_text", None)
            if text is None or not str(text).strip():
                result.add_error(f"question_{idx}", f"Question {idx} text is required")

        # Max attempts range (1..5)
        max_attempts = getattr(campaign, "max_attempts", None)
        if not isinstance(max_attempts, int) or not (1 <= max_attempts <= 5):
            result.add_error("max_attempts", "max_attempts must be between 1 and 5")

        # Allowed call window required and must be start < end
        start = getattr(campaign, "allowed_call_start_local", None)
        end = getattr(campaign, "allowed_call_end_local", None)

        if start is None or end is None:
            result.add_error("allowed_call_window", "allowed_call_start_local and allowed_call_end_local are required")
        else:
            if not isinstance(start, time) or not isinstance(end, time) or start >= end:
                result.add_error("allowed_call_window", "allowed_call time window is invalid")

        return result

    async def activate_campaign(self, campaign_id: UUID) -> Campaign:
        campaign = await self._campaign_repo.get_by_id(campaign_id)
        if campaign is None:
            raise ValidationError("Campaign not found", details=[{"field": "campaign", "message": "Campaign not found"}])

        if campaign.status != CampaignStatus.DRAFT:
            raise ValidationError(
                "Campaign status must be draft to activate",
                details=[{"field": "status", "message": "Campaign must be in DRAFT status"}],
            )

        validation = await self.validate_for_activation(campaign_id)
        if not validation.is_valid:
            raise ValidationError("Campaign validation failed", details=validation.errors)

        campaign.status = CampaignStatus.RUNNING
        updated = await self._campaign_repo.update(campaign)
        return updated if updated is not None else campaign
