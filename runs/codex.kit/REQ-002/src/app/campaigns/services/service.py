from __future__ import annotations

from typing import Mapping, Optional
from uuid import UUID

from app.auth.domain.models import UserPrincipal
from app.campaigns.domain.commands import CampaignCreateCommand, CampaignUpdateCommand
from app.campaigns.domain.enums import CampaignStatus
from app.campaigns.domain.errors import (
    CampaignActivationError,
    CampaignNotFoundError,
    CampaignStatusError,
    CampaignValidationError,
)
from app.campaigns.domain.models import CampaignRecord
from app.campaigns.domain.validators import (
    validate_campaign_definition,
    validate_update_payload,
)
from app.campaigns.services.interfaces import (
    CampaignFilters,
    CampaignListResult,
    CampaignRepository,
    ContactStatsProvider,
    PaginationParams,
    PaginationResult,
)


class CampaignService:
    MUTABLE_STATUSES = {
        CampaignStatus.draft.value,
        CampaignStatus.paused.value,
    }
    ACTIVATABLE_STATUSES = {
        CampaignStatus.draft.value,
        CampaignStatus.paused.value,
        CampaignStatus.scheduled.value,
    }

    def __init__(
        self,
        repository: CampaignRepository,
        contact_stats_provider: ContactStatsProvider,
    ) -> None:
        self.repository = repository
        self.contact_stats_provider = contact_stats_provider

    def create_campaign(
        self, command: CampaignCreateCommand, user: UserPrincipal
    ) -> CampaignRecord:
        validate_campaign_definition(command)
        record = self.repository.create(
            self._command_to_payload(command),
            created_by=user.id,
        )
        return record

    def update_campaign(
        self, campaign_id: UUID, command: CampaignUpdateCommand
    ) -> CampaignRecord:
        campaign = self._get_or_raise(campaign_id)
        if campaign.status.value not in self.MUTABLE_STATUSES:
            raise CampaignStatusError(
                f"Campaign in '{campaign.status.value}' cannot be edited."
            )
        validate_update_payload(command)
        update_payload = self._command_to_update_payload(command)
        if not update_payload:
            raise CampaignValidationError("No updatable fields were provided.")
        return self.repository.update(campaign_id, update_payload)

    def list_campaigns(
        self, filters: CampaignFilters, pagination: PaginationParams
    ) -> CampaignListResult:
        items, total = self.repository.list(filters, pagination)
        return CampaignListResult(
            items=list(items),
            pagination=PaginationResult(
                page=pagination.page,
                page_size=pagination.page_size,
                total_items=total,
            ),
        )

    def get_campaign(self, campaign_id: UUID) -> CampaignRecord:
        return self._get_or_raise(campaign_id)

    def activate_campaign(self, campaign_id: UUID) -> CampaignRecord:
        campaign = self._get_or_raise(campaign_id)
        if campaign.status.value not in self.ACTIVATABLE_STATUSES:
            raise CampaignStatusError(
                f"Cannot activate campaign in status '{campaign.status.value}'."
            )
        stats = self.contact_stats_provider.get_stats(campaign_id)
        if stats.eligible_contacts <= 0:
            raise CampaignActivationError(
                "At least one eligible contact is required before activation."
            )
        if len(campaign.questions) != 3:
            raise CampaignActivationError("Campaign must have exactly three questions.")
        if not campaign.intro_script.strip():
            raise CampaignActivationError("Intro script must be configured before activation.")
        return self.repository.update_status(campaign_id, CampaignStatus.running.value)

    def pause_campaign(self, campaign_id: UUID) -> CampaignRecord:
        campaign = self._get_or_raise(campaign_id)
        if campaign.status is not CampaignStatus.running:
            raise CampaignStatusError("Only running campaigns can be paused.")
        return self.repository.update_status(campaign_id, CampaignStatus.paused.value)

    def _get_or_raise(self, campaign_id: UUID) -> CampaignRecord:
        campaign = self.repository.get(campaign_id)
        if campaign is None:
            raise CampaignNotFoundError("Campaign was not found.")
        return campaign

    @staticmethod
    def _command_to_payload(command: CampaignCreateCommand) -> Mapping[str, object]:
        questions = list(command.questions)
        return {
            "name": command.name,
            "description": command.description,
            "status": CampaignStatus.draft.value,
            "language": command.language.value,
            "intro_script": command.intro_script,
            "question_1_text": questions[0].text,
            "question_1_type": questions[0].answer_type.value,
            "question_2_text": questions[1].text,
            "question_2_type": questions[1].answer_type.value,
            "question_3_text": questions[2].text,
            "question_3_type": questions[2].answer_type.value,
            "max_attempts": command.retry_policy.max_attempts,
            "retry_interval_minutes": command.retry_policy.retry_interval_minutes,
            "allowed_call_start_local": command.call_window.start_local,
            "allowed_call_end_local": command.call_window.end_local,
            "email_completed_template_id": command.email_completed_template_id,
            "email_refused_template_id": command.email_refused_template_id,
            "email_not_reached_template_id": command.email_not_reached_template_id,
        }

    @staticmethod
    def _command_to_update_payload(command: CampaignUpdateCommand) -> Mapping[str, object]:
        payload: dict[str, object] = {}
        if command.name is not None:
            payload["name"] = command.name
        if command.description is not None:
            payload["description"] = command.description
        if command.language is not None:
            payload["language"] = command.language.value
        if command.intro_script is not None:
            payload["intro_script"] = command.intro_script
        if command.questions is not None:
            questions = list(command.questions)
            payload.update(
                {
                    "question_1_text": questions[0].text,
                    "question_1_type": questions[0].answer_type.value,
                    "question_2_text": questions[1].text,
                    "question_2_type": questions[1].answer_type.value,
                    "question_3_text": questions[2].text,
                    "question_3_type": questions[2].answer_type.value,
                }
            )
        if command.retry_policy is not None:
            payload["max_attempts"] = command.retry_policy.max_attempts
            payload["retry_interval_minutes"] = command.retry_policy.retry_interval_minutes
        if command.call_window is not None:
            payload["allowed_call_start_local"] = command.call_window.start_local
            payload["allowed_call_end_local"] = command.call_window.end_local
        if command.email_completed_template_id is not None:
            payload["email_completed_template_id"] = command.email_completed_template_id
        if command.email_refused_template_id is not None:
            payload["email_refused_template_id"] = command.email_refused_template_id
        if command.email_not_reached_template_id is not None:
            payload["email_not_reached_template_id"] = command.email_not_reached_template_id
        return payload