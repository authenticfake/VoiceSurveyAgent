"""
Campaign activation API router.

REQ-005: Campaign validation service
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import CurrentUser
from app.auth.rbac import require_campaign_manager
from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import CampaignResponse, ValidationErrorResponse
from app.campaigns.validation import CampaignValidationService
from app.contacts.repository import ContactRepository
from app.shared.database import get_db_session
from app.shared.exceptions import ValidationError
from app.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def get_validation_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignValidationService:
    """Dependency for campaign validation service."""
    campaign_repo = CampaignRepository(session)
    contact_repo = ContactRepository(session)
    return CampaignValidationService(
        campaign_repository=campaign_repo,
        contact_repository=contact_repo,
    )


@router.post(
    "/{campaign_id}/activate",
    response_model=CampaignResponse,
    responses={
        400: {"model": ValidationErrorResponse, "description": "Validation failed"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Campaign not found"},
    },
)
async def activate_campaign(
    campaign_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    service: Annotated[CampaignValidationService, Depends(get_validation_service)],
) -> CampaignResponse:
    """Activate a campaign after validation.

    Validates the campaign configuration and transitions status to 'running'
    if all validation checks pass.

    Validation checks:
    - Campaign has at least one contact
    - All 3 questions are non-empty
    - Retry policy is valid (1-5 attempts)
    - Time window is valid (start < end)

    Args:
        campaign_id: Campaign UUID to activate.
        current_user: Authenticated user (campaign_manager or admin).
        service: Campaign validation service.

    Returns:
        Updated campaign with 'running' status.

    Raises:
        HTTPException: 400 if validation fails, 404 if not found.
    """
    logger.info(
        "Campaign activation requested",
        extra={
            "campaign_id": str(campaign_id),
            "user_id": str(current_user.id),
            "user_role": current_user.role,
        },
    )

    try:
        campaign = await service.activate_campaign(campaign_id)

        logger.info(
            "Campaign activated",
            extra={
                "campaign_id": str(campaign_id),
                "user_id": str(current_user.id),
            },
        )

        return CampaignResponse.model_validate(campaign)

    except ValidationError as e:
        logger.warning(
            "Campaign activation failed - validation error",
            extra={
                "campaign_id": str(campaign_id),
                "user_id": str(current_user.id),
                "error": str(e),
                "details": getattr(e, "details", None),
            },
        )

        # Check if it's a "not found" error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "CAMPAIGN_NOT_FOUND",
                    "message": "Campaign not found",
                },
            )

        # Return validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_FAILED",
                "message": str(e),
                "errors": getattr(e, "details", []),
            },
        )