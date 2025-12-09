"""
Campaign validation service.

REQ-005: Campaign validation service
"""

from datetime import time
from typing import Protocol
from uuid import UUID

from app.campaigns.models import Campaign, CampaignStatus
from app.campaigns.repository import CampaignRepositoryProtocol
from app.shared.exceptions import ValidationError
from app.shared.logging import get_logger

logger = get_logger(__name__)


class ContactRepositoryProtocol(Protocol):
    """Protocol for contact repository operations needed by validation."""

    async def count_by_campaign(self, campaign_id: UUID) -> int:
        """Count contacts for a campaign.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            Number of contacts.
        """
        ...


class ValidationResult:
    """Result of campaign validation."""

    def __init__(self) -> None:
        """Initialize validation result."""
        self._errors: list[dict[str, str]] = []
        self._is_valid: bool = True

    def add_error(self, field: str, message: str) -> None:
        """Add a validation error.

        Args:
            field: Field name that failed validation.
            message: Error message.
        """
        self._errors.append({"field": field, "message": message})
        self._is_valid = False

    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self._is_valid

    @property
    def errors(self) -> list[dict[str, str]]:
        """Get list of validation errors."""
        return self._errors.copy()


class CampaignValidationService:
    """Service for validating campaign configuration before activation."""

    def __init__(
        self,
        campaign_repository: CampaignRepositoryProtocol,
        contact_repository: ContactRepositoryProtocol,
    ) -> None:
        """Initialize validation service.

        Args:
            campaign_repository: Repository for campaign operations.
            contact_repository: Repository for contact operations.
        """
        self._campaign_repo = campaign_repository
        self._contact_repo = contact_repository

    async def validate_for_activation(
        self,
        campaign_id: UUID,
    ) -> ValidationResult:
        """Validate campaign configuration for activation.

        Checks:
        - Campaign has at least one contact
        - All 3 questions are non-empty
        - Retry policy is valid (1-5 attempts)
        - Time window is valid (start < end)

        Args:
            campaign_id: Campaign UUID to validate.

        Returns:
            ValidationResult with any errors found.

        Raises:
            ValidationError: If campaign not found.
        """
        result = ValidationResult()

        # Get campaign
        campaign = await self._campaign_repo.get_by_id(campaign_id)
        if campaign is None:
            raise ValidationError(
                message="Campaign not found",
                field="campaign_id",
            )

        logger.info(
            "Validating campaign for activation",
            extra={
                "campaign_id": str(campaign_id),
                "campaign_name": campaign.name,
                "current_status": campaign.status.value,
            },
        )

        # Check contact count
        contact_count = await self._contact_repo.count_by_campaign(campaign_id)
        if contact_count == 0:
            result.add_error(
                field="contacts",
                message="Campaign must have at least one contact",
            )
            logger.warning(
                "Campaign has no contacts",
                extra={"campaign_id": str(campaign_id)},
            )

        # Check questions
        self._validate_questions(campaign, result)

        # Check retry policy
        self._validate_retry_policy(campaign, result)

        # Check time window
        self._validate_time_window(campaign, result)

        if result.is_valid:
            logger.info(
                "Campaign validation passed",
                extra={
                    "campaign_id": str(campaign_id),
                    "contact_count": contact_count,
                },
            )
        else:
            logger.warning(
                "Campaign validation failed",
                extra={
                    "campaign_id": str(campaign_id),
                    "error_count": len(result.errors),
                    "errors": result.errors,
                },
            )

        return result

    def _validate_questions(
        self,
        campaign: Campaign,
        result: ValidationResult,
    ) -> None:
        """Validate that all 3 questions are non-empty.

        Args:
            campaign: Campaign to validate.
            result: ValidationResult to add errors to.
        """
        questions = [
            ("question_1_text", campaign.question_1_text),
            ("question_2_text", campaign.question_2_text),
            ("question_3_text", campaign.question_3_text),
        ]

        for field_name, question_text in questions:
            if not question_text or not question_text.strip():
                result.add_error(
                    field=field_name,
                    message=f"{field_name} cannot be empty",
                )

    def _validate_retry_policy(
        self,
        campaign: Campaign,
        result: ValidationResult,
    ) -> None:
        """Validate retry policy (1-5 attempts).

        Args:
            campaign: Campaign to validate.
            result: ValidationResult to add errors to.
        """
        if campaign.max_attempts < 1:
            result.add_error(
                field="max_attempts",
                message="Maximum attempts must be at least 1",
            )
        elif campaign.max_attempts > 5:
            result.add_error(
                field="max_attempts",
                message="Maximum attempts cannot exceed 5",
            )

    def _validate_time_window(
        self,
        campaign: Campaign,
        result: ValidationResult,
    ) -> None:
        """Validate time window (start < end).

        Args:
            campaign: Campaign to validate.
            result: ValidationResult to add errors to.
        """
        start_time = campaign.allowed_call_start_local
        end_time = campaign.allowed_call_end_local

        if start_time is None or end_time is None:
            result.add_error(
                field="time_window",
                message="Call time window must be configured",
            )
            return

        # Compare times - start must be strictly before end
        if start_time >= end_time:
            result.add_error(
                field="time_window",
                message="Call start time must be before end time",
            )

    async def activate_campaign(
        self,
        campaign_id: UUID,
    ) -> Campaign:
        """Validate and activate a campaign.

        Validates the campaign configuration and transitions status
        to 'running' or 'scheduled' if validation passes.

        Args:
            campaign_id: Campaign UUID to activate.

        Returns:
            Updated campaign with new status.

        Raises:
            ValidationError: If validation fails or campaign not found.
        """
        # Validate first
        validation_result = await self.validate_for_activation(campaign_id)

        if not validation_result.is_valid:
            raise ValidationError(
                message="Campaign validation failed",
                field="campaign",
                details=validation_result.errors,
            )

        # Get campaign for status transition
        campaign = await self._campaign_repo.get_by_id(campaign_id)
        if campaign is None:
            raise ValidationError(
                message="Campaign not found",
                field="campaign_id",
            )

        # Check current status allows activation
        if campaign.status != CampaignStatus.DRAFT:
            raise ValidationError(
                message=f"Cannot activate campaign with status '{campaign.status.value}'",
                field="status",
            )

        # Transition to running (immediate activation)
        # In future, could check scheduled_at to determine running vs scheduled
        campaign.status = CampaignStatus.RUNNING

        # Persist the change
        updated_campaign = await self._campaign_repo.update(campaign)

        logger.info(
            "Campaign activated successfully",
            extra={
                "campaign_id": str(campaign_id),
                "new_status": updated_campaign.status.value,
            },
        )

        return updated_campaign