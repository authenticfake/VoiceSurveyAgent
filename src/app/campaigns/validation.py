from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

from app.campaigns.models import Campaign, CampaignStatus
from app.shared.exceptions import ValidationError


class CampaignRepository(Protocol):
    async def get_by_id(self, campaign_id: UUID) -> Campaign | None: ...
    async def update(self, campaign: Campaign) -> Campaign: ...


class ContactRepository(Protocol):
    async def count_by_campaign(self, campaign_id: UUID) -> int: ...


@dataclass
class ValidationResult:
    """
    Mutable validation result expected by tests.

    - default is_valid=True
    - add_error() flips is_valid=False and appends {"field": ..., "message": ...}
    - errors property returns a COPY
    """

    is_valid: bool = True
    _errors: List[Dict[str, str]] = field(default_factory=list, repr=False)

    def add_error(self, field: str, message: str) -> None:
        self.is_valid = False
        self._errors.append({"field": field, "message": message})

    @property
    def errors(self) -> List[Dict[str, str]]:
        return list(self._errors)


class CampaignValidationService:
    def __init__(
        self,
        campaign_repository: CampaignRepository,
        contact_repository: ContactRepository,
        **_kwargs: Any,  # tolerate extra kwargs
    ) -> None:
        self._campaign_repository = campaign_repository
        self._contact_repository = contact_repository

    async def validate_for_activation(self, campaign_id: UUID) -> ValidationResult:
        campaign = await self._campaign_repository.get_by_id(campaign_id)
        if campaign is None:
            raise ValidationError(
                "Campaign not found",
                details={"campaign_id": "Campaign not found"},
            )

        result = ValidationResult()

        contact_count = await self._contact_repository.count_by_campaign(campaign_id)
        if contact_count == 0:
            result.add_error("contacts", "Campaign must have at least one contact")

        self._validate_questions(campaign, result)
        self._validate_max_attempts(campaign, result)
        self._validate_time_window(campaign, result)

        return result

    async def activate_campaign(self, campaign_id: UUID) -> Campaign:
        campaign = await self._campaign_repository.get_by_id(campaign_id)
        if campaign is None:
            raise ValidationError(
                "Campaign not found",
                details={"campaign_id": "Campaign not found"},
            )

        if campaign.status != CampaignStatus.DRAFT:
            raise ValidationError(
                "Campaign must be in draft status to activate",
                details={"status": "Campaign must be in draft status to activate"},
            )

        result = await self.validate_for_activation(campaign_id)
        if not result.is_valid:
            # tests want details non-empty
            raise ValidationError("campaign validation failed", details={"errors": result.errors})

        campaign.status = CampaignStatus.RUNNING
        return await self._campaign_repository.update(campaign)

    @staticmethod
    def _is_blank(value: Optional[str]) -> bool:
        return value is None or value.strip() == ""

    def _validate_questions(self, campaign: Campaign, result: ValidationResult) -> None:
        if self._is_blank(campaign.question_1_text):
            result.add_error("question_1_text", "Question 1 text is required")
        if self._is_blank(campaign.question_2_text):
            result.add_error("question_2_text", "Question 2 text is required")
        if self._is_blank(campaign.question_3_text):
            result.add_error("question_3_text", "Question 3 text is required")

    def _validate_max_attempts(self, campaign: Campaign, result: ValidationResult) -> None:
        if campaign.max_attempts < 1:
            result.add_error("max_attempts", "max_attempts must be >= 1")
        if campaign.max_attempts > 5:
            result.add_error("max_attempts", "max_attempts must be <= 5")

    def _validate_time_window(self, campaign: Campaign, result: ValidationResult) -> None:
        start = campaign.allowed_call_start_local
        end = campaign.allowed_call_end_local

        if start is None or end is None:
            result.add_error("time_window", "Time window must be configured")
            return

        if isinstance(start, str):
            start = time.fromisoformat(start)
        if isinstance(end, str):
            end = time.fromisoformat(end)

        if start == end:
            result.add_error("time_window", "Start and end times cannot be equal")
            return

        if start > end:
            result.add_error("time_window", "Start time must be before end time")
