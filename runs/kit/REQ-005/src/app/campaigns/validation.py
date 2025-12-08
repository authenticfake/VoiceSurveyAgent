"""
Campaign validation service.

Validates campaign configuration before activation, ensuring all required
fields are properly configured and business rules are satisfied.
"""

from dataclasses import dataclass
from datetime import time
from typing import Optional
from uuid import UUID

from app.campaigns.repository import CampaignRepository
from app.shared.exceptions import ValidationError
from app.shared.logging import get_logger
from app.shared.models.enums import CampaignStatus

logger = get_logger(__name__)

@dataclass(frozen=True)
class ValidationResult:
    """Result of campaign validation."""
    
    is_valid: bool
    errors: list[str]
    
    @classmethod
    def success(cls) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(is_valid=True, errors=[])
    
    @classmethod
    def failure(cls, errors: list[str]) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(is_valid=False, errors=errors)

class CampaignValidationService:
    """
    Service for validating campaign configuration before activation.
    
    Validates:
    - Campaign has at least one contact
    - All 3 questions are non-empty
    - Retry policy is valid (1-5 attempts)
    - Time window is valid (start < end)
    """
    
    def __init__(self, repository: CampaignRepository) -> None:
        """
        Initialize validation service.
        
        Args:
            repository: Campaign repository for data access
        """
        self._repository = repository
    
    async def validate_for_activation(
        self,
        campaign_id: UUID,
    ) -> ValidationResult:
        """
        Validate campaign configuration for activation.
        
        Args:
            campaign_id: UUID of the campaign to validate
            
        Returns:
            ValidationResult with validation status and any errors
            
        Raises:
            NotFoundError: If campaign does not exist
        """
        campaign = await self._repository.get_by_id(campaign_id)
        if campaign is None:
            from app.shared.exceptions import NotFoundError
            raise NotFoundError(f"Campaign {campaign_id} not found")
        
        errors: list[str] = []
        
        # Check campaign status - must be in draft to activate
        if campaign.status != CampaignStatus.DRAFT:
            errors.append(
                f"Campaign must be in draft status to activate, "
                f"current status: {campaign.status.value}"
            )
        
        # Validate contacts exist
        contact_count = await self._repository.get_contact_count(campaign_id)
        if contact_count == 0:
            errors.append("Campaign must have at least one contact")
        
        # Validate questions are non-empty
        if not campaign.question_1_text or not campaign.question_1_text.strip():
            errors.append("Question 1 text is required")
        if not campaign.question_2_text or not campaign.question_2_text.strip():
            errors.append("Question 2 text is required")
        if not campaign.question_3_text or not campaign.question_3_text.strip():
            errors.append("Question 3 text is required")
        
        # Validate retry policy
        if campaign.max_attempts < 1 or campaign.max_attempts > 5:
            errors.append(
                f"Max attempts must be between 1 and 5, "
                f"got: {campaign.max_attempts}"
            )
        
        # Validate time window
        if campaign.allowed_call_start_local >= campaign.allowed_call_end_local:
            errors.append(
                f"Call start time ({campaign.allowed_call_start_local}) "
                f"must be before end time ({campaign.allowed_call_end_local})"
            )
        
        if errors:
            logger.warning(
                "Campaign validation failed",
                extra={
                    "campaign_id": str(campaign_id),
                    "error_count": len(errors),
                    "errors": errors,
                },
            )
            return ValidationResult.failure(errors)
        
        logger.info(
            "Campaign validation passed",
            extra={"campaign_id": str(campaign_id)},
        )
        return ValidationResult.success()
    
    async def activate_campaign(
        self,
        campaign_id: UUID,
    ) -> None:
        """
        Validate and activate a campaign.
        
        Performs validation and transitions campaign status to running
        if validation passes.
        
        Args:
            campaign_id: UUID of the campaign to activate
            
        Raises:
            ValidationError: If validation fails
            NotFoundError: If campaign does not exist
        """
        result = await self.validate_for_activation(campaign_id)
        
        if not result.is_valid:
            raise ValidationError(
                message="Campaign validation failed",
                details={"errors": result.errors},
            )
        
        # Transition to running status
        await self._repository.update_status(campaign_id, CampaignStatus.RUNNING)
        
        logger.info(
            "Campaign activated successfully",
            extra={
                "campaign_id": str(campaign_id),
                "new_status": CampaignStatus.RUNNING.value,
            },
        )