"""Campaign validation service for activation checks."""

from dataclasses import dataclass, field
from datetime import time
from typing import Protocol
from uuid import UUID

from app.shared.logging import get_logger
from app.shared.models.enums import CampaignStatus

logger = get_logger(__name__)

@dataclass
class ValidationError:
    """Single validation error with field and message."""
    
    field: str
    message: str
    code: str

@dataclass
class ValidationResult:
    """Result of campaign validation."""
    
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    
    def add_error(self, field: str, message: str, code: str) -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(field=field, message=message, code=code))
        self.is_valid = False

class CampaignDataProvider(Protocol):
    """Protocol for providing campaign data for validation."""
    
    async def get_contact_count(self, campaign_id: UUID) -> int:
        """Get the number of contacts for a campaign."""
        ...
    
    async def get_campaign_questions(self, campaign_id: UUID) -> tuple[str, str, str]:
        """Get the three question texts for a campaign."""
        ...
    
    async def get_retry_policy(self, campaign_id: UUID) -> tuple[int, int]:
        """Get max_attempts and retry_interval_minutes."""
        ...
    
    async def get_time_window(self, campaign_id: UUID) -> tuple[time, time]:
        """Get allowed_call_start_local and allowed_call_end_local."""
        ...
    
    async def get_campaign_status(self, campaign_id: UUID) -> CampaignStatus:
        """Get current campaign status."""
        ...

class CampaignValidationService:
    """Service for validating campaign activation requirements."""
    
    def __init__(self, data_provider: CampaignDataProvider) -> None:
        """Initialize with a data provider."""
        self._data_provider = data_provider
    
    async def validate_for_activation(self, campaign_id: UUID) -> ValidationResult:
        """
        Validate a campaign for activation.
        
        Checks:
        1. Campaign has at least one contact
        2. All three questions are non-empty
        3. Retry policy is valid (1-5 attempts)
        4. Time window is valid (start < end)
        5. Campaign is in draft status
        
        Args:
            campaign_id: The campaign to validate
            
        Returns:
            ValidationResult with is_valid flag and any errors
        """
        result = ValidationResult(is_valid=True)
        
        # Check campaign status first
        status = await self._data_provider.get_campaign_status(campaign_id)
        if status != CampaignStatus.DRAFT:
            result.add_error(
                field="status",
                message=f"Campaign must be in draft status to activate, current status: {status.value}",
                code="INVALID_STATUS",
            )
            logger.warning(
                "Campaign activation blocked - invalid status",
                extra={"campaign_id": str(campaign_id), "status": status.value},
            )
            return result  # Early return - no point checking other fields
        
        # Check contact count
        contact_count = await self._data_provider.get_contact_count(campaign_id)
        if contact_count == 0:
            result.add_error(
                field="contacts",
                message="Campaign must have at least one contact",
                code="NO_CONTACTS",
            )
            logger.warning(
                "Campaign activation blocked - no contacts",
                extra={"campaign_id": str(campaign_id)},
            )
        
        # Check questions
        q1, q2, q3 = await self._data_provider.get_campaign_questions(campaign_id)
        if not q1 or not q1.strip():
            result.add_error(
                field="question_1_text",
                message="Question 1 cannot be empty",
                code="EMPTY_QUESTION",
            )
        if not q2 or not q2.strip():
            result.add_error(
                field="question_2_text",
                message="Question 2 cannot be empty",
                code="EMPTY_QUESTION",
            )
        if not q3 or not q3.strip():
            result.add_error(
                field="question_3_text",
                message="Question 3 cannot be empty",
                code="EMPTY_QUESTION",
            )
        
        # Check retry policy
        max_attempts, retry_interval = await self._data_provider.get_retry_policy(campaign_id)
        if max_attempts < 1 or max_attempts > 5:
            result.add_error(
                field="max_attempts",
                message=f"Max attempts must be between 1 and 5, got {max_attempts}",
                code="INVALID_RETRY_POLICY",
            )
            logger.warning(
                "Campaign activation blocked - invalid retry policy",
                extra={"campaign_id": str(campaign_id), "max_attempts": max_attempts},
            )
        
        # Check time window
        start_time, end_time = await self._data_provider.get_time_window(campaign_id)
        if start_time >= end_time:
            result.add_error(
                field="allowed_call_start_local",
                message=f"Call start time ({start_time}) must be before end time ({end_time})",
                code="INVALID_TIME_WINDOW",
            )
            logger.warning(
                "Campaign activation blocked - invalid time window",
                extra={
                    "campaign_id": str(campaign_id),
                    "start_time": str(start_time),
                    "end_time": str(end_time),
                },
            )
        
        if result.is_valid:
            logger.info(
                "Campaign validation passed",
                extra={"campaign_id": str(campaign_id), "contact_count": contact_count},
            )
        else:
            logger.warning(
                "Campaign validation failed",
                extra={
                    "campaign_id": str(campaign_id),
                    "error_count": len(result.errors),
                    "error_codes": [e.code for e in result.errors],
                },
            )
        
        return result