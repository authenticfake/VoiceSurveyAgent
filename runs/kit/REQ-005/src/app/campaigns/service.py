"""Campaign service for business logic."""

from typing import Optional, Sequence
from uuid import UUID

from app.campaigns.repository import CampaignRepository
from app.campaigns.validation import CampaignValidationService, ValidationResult
from app.shared.exceptions import NotFoundError, StateTransitionError, ValidationError
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Valid status transitions
VALID_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.DRAFT: {CampaignStatus.SCHEDULED, CampaignStatus.RUNNING, CampaignStatus.CANCELLED},
    CampaignStatus.SCHEDULED: {CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.CANCELLED},
    CampaignStatus.RUNNING: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
    CampaignStatus.PAUSED: {CampaignStatus.RUNNING, CampaignStatus.CANCELLED},
    CampaignStatus.COMPLETED: set(),  # Terminal state
    CampaignStatus.CANCELLED: set(),  # Terminal state
}

class CampaignService:
    """Service for campaign business logic."""
    
    def __init__(
        self,
        repository: CampaignRepository,
        validation_service: Optional[CampaignValidationService] = None,
    ) -> None:
        """Initialize with repository and optional validation service."""
        self._repository = repository
        self._validation_service = validation_service or CampaignValidationService(repository)
    
    async def create_campaign(
        self,
        name: str,
        intro_script: str,
        question_1_text: str,
        question_1_type: str,
        question_2_text: str,
        question_2_type: str,
        question_3_text: str,
        question_3_type: str,
        created_by_user_id: UUID,
        **kwargs,
    ) -> Campaign:
        """Create a new campaign in draft status."""
        from app.shared.models.enums import LanguageCode, QuestionType
        
        campaign = Campaign(
            name=name,
            intro_script=intro_script,
            question_1_text=question_1_text,
            question_1_type=QuestionType(question_1_type),
            question_2_text=question_2_text,
            question_2_type=QuestionType(question_2_type),
            question_3_text=question_3_text,
            question_3_type=QuestionType(question_3_type),
            created_by_user_id=created_by_user_id,
            status=CampaignStatus.DRAFT,
            language=LanguageCode(kwargs.get("language", "en")),
            description=kwargs.get("description"),
            max_attempts=kwargs.get("max_attempts", 3),
            retry_interval_minutes=kwargs.get("retry_interval_minutes", 60),
            allowed_call_start_local=kwargs.get("allowed_call_start_local"),
            allowed_call_end_local=kwargs.get("allowed_call_end_local"),
            email_completed_template_id=kwargs.get("email_completed_template_id"),
            email_refused_template_id=kwargs.get("email_refused_template_id"),
            email_not_reached_template_id=kwargs.get("email_not_reached_template_id"),
        )
        
        return await self._repository.create(campaign)
    
    async def get_campaign(self, campaign_id: UUID) -> Campaign:
        """Get a campaign by ID."""
        campaign = await self._repository.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        return campaign
    
    async def list_campaigns(
        self,
        status: Optional[CampaignStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Campaign], int]:
        """List campaigns with optional filtering."""
        return await self._repository.list_campaigns(status, page, page_size)
    
    async def update_campaign(
        self,
        campaign_id: UUID,
        **updates,
    ) -> Campaign:
        """Update a campaign."""
        campaign = await self.get_campaign(campaign_id)
        
        # Check if campaign can be updated (only draft campaigns)
        if campaign.status != CampaignStatus.DRAFT:
            raise StateTransitionError(
                f"Cannot update campaign in {campaign.status.value} status"
            )
        
        # Apply updates
        for field, value in updates.items():
            if value is not None and hasattr(campaign, field):
                setattr(campaign, field, value)
        
        return await self._repository.update(campaign)
    
    async def update_status(
        self,
        campaign_id: UUID,
        new_status: CampaignStatus,
    ) -> Campaign:
        """Update campaign status with validation."""
        campaign = await self.get_campaign(campaign_id)
        
        # Check if transition is valid
        valid_next_states = VALID_TRANSITIONS.get(campaign.status, set())
        if new_status not in valid_next_states:
            raise StateTransitionError(
                f"Cannot transition from {campaign.status.value} to {new_status.value}"
            )
        
        campaign.status = new_status
        return await self._repository.update(campaign)
    
    async def delete_campaign(self, campaign_id: UUID) -> Campaign:
        """Soft delete a campaign."""
        campaign = await self.get_campaign(campaign_id)
        return await self._repository.soft_delete(campaign)
    
    async def validate_for_activation(self, campaign_id: UUID) -> ValidationResult:
        """Validate a campaign for activation."""
        # Ensure campaign exists
        await self.get_campaign(campaign_id)
        return await self._validation_service.validate_for_activation(campaign_id)
    
    async def activate_campaign(self, campaign_id: UUID) -> Campaign:
        """
        Activate a campaign after validation.
        
        Validates the campaign and transitions to running status if valid.
        
        Args:
            campaign_id: The campaign to activate
            
        Returns:
            The activated campaign
            
        Raises:
            ValidationError: If validation fails
            StateTransitionError: If campaign cannot be activated
        """
        # Validate first
        validation_result = await self.validate_for_activation(campaign_id)
        
        if not validation_result.is_valid:
            error_messages = [
                f"{e.field}: {e.message}" for e in validation_result.errors
            ]
            raise ValidationError(
                f"Campaign validation failed: {'; '.join(error_messages)}"
            )
        
        # Transition to running
        return await self.update_status(campaign_id, CampaignStatus.RUNNING)