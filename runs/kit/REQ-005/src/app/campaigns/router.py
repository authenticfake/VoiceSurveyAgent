"""Campaign API router with validation and activation endpoints."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.middleware import CurrentUser, require_role
from app.auth.schemas import UserRole
from app.campaigns.schemas import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
    CampaignStatusUpdate,
    ValidationResultResponse,
    ActivationResponse,
)
from app.campaigns.service import CampaignService
from app.campaigns.validation import CampaignValidationService
from app.campaigns.repository import CampaignRepository
from app.shared.database import DbSession
from app.shared.exceptions import (
    NotFoundError,
    ValidationError,
    StateTransitionError,
)
from app.shared.models.enums import CampaignStatus
from app.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

async def get_campaign_service(db: DbSession) -> CampaignService:
    """Dependency to get campaign service instance."""
    repository = CampaignRepository(db)
    return CampaignService(repository)

CampaignServiceDep = Annotated[CampaignService, Depends(get_campaign_service)]

@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new campaign",
    description="Create a new campaign in draft status",
)
async def create_campaign(
    campaign_data: CampaignCreate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
) -> CampaignResponse:
    """Create a new campaign."""
    campaign = await service.create_campaign(
        name=campaign_data.name,
        intro_script=campaign_data.intro_script,
        question_1_text=campaign_data.question_1_text,
        question_1_type=campaign_data.question_1_type.value,
        question_2_text=campaign_data.question_2_text,
        question_2_type=campaign_data.question_2_type.value,
        question_3_text=campaign_data.question_3_text,
        question_3_type=campaign_data.question_3_type.value,
        created_by_user_id=current_user.id,
        description=campaign_data.description,
        language=campaign_data.language.value,
        max_attempts=campaign_data.max_attempts,
        retry_interval_minutes=campaign_data.retry_interval_minutes,
        allowed_call_start_local=campaign_data.allowed_call_start_local,
        allowed_call_end_local=campaign_data.allowed_call_end_local,
        email_completed_template_id=campaign_data.email_completed_template_id,
        email_refused_template_id=campaign_data.email_refused_template_id,
        email_not_reached_template_id=campaign_data.email_not_reached_template_id,
    )
    logger.info(
        "Campaign created via API",
        extra={"campaign_id": str(campaign.id), "user_id": str(current_user.id)},
    )
    return CampaignResponse.model_validate(campaign)

@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List campaigns",
    description="List campaigns with optional status filter and pagination",
)
async def list_campaigns(
    service: CampaignServiceDep,
    current_user: CurrentUser,
    status_filter: Optional[CampaignStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CampaignListResponse:
    """List campaigns with pagination."""
    campaigns, total = await service.list_campaigns(status_filter, page, page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return CampaignListResponse(
        items=[
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "language": c.language,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in campaigns
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get campaign details",
    description="Get full details of a specific campaign",
)
async def get_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Get campaign by ID."""
    try:
        campaign = await service.get_campaign(campaign_id)
        return CampaignResponse.model_validate(campaign)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update campaign",
    description="Update campaign fields (only allowed for draft campaigns)",
)
async def update_campaign(
    campaign_id: UUID,
    campaign_data: CampaignUpdate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
) -> CampaignResponse:
    """Update a campaign."""
    try:
        updates = campaign_data.model_dump(exclude_unset=True)
        campaign = await service.update_campaign(campaign_id, **updates)
        logger.info(
            "Campaign updated via API",
            extra={"campaign_id": str(campaign_id), "user_id": str(current_user.id)},
        )
        return CampaignResponse.model_validate(campaign)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.patch(
    "/{campaign_id}/status",
    response_model=CampaignResponse,
    summary="Update campaign status",
    description="Update campaign status following valid state transitions",
)
async def update_campaign_status(
    campaign_id: UUID,
    status_update: CampaignStatusUpdate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
) -> CampaignResponse:
    """Update campaign status."""
    try:
        campaign = await service.update_status(campaign_id, status_update.status)
        logger.info(
            "Campaign status updated via API",
            extra={
                "campaign_id": str(campaign_id),
                "new_status": status_update.status.value,
                "user_id": str(current_user.id),
            },
        )
        return CampaignResponse.model_validate(campaign)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.delete(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Delete campaign",
    description="Soft delete a campaign by setting status to cancelled",
)
async def delete_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
) -> CampaignResponse:
    """Soft delete a campaign."""
    try:
        campaign = await service.delete_campaign(campaign_id)
        logger.info(
            "Campaign deleted via API",
            extra={"campaign_id": str(campaign_id), "user_id": str(current_user.id)},
        )
        return CampaignResponse.model_validate(campaign)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

@router.get(
    "/{campaign_id}/validate",
    response_model=ValidationResultResponse,
    summary="Validate campaign for activation",
    description="Check if a campaign meets all requirements for activation",
)
async def validate_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
) -> ValidationResultResponse:
    """Validate a campaign for activation."""
    try:
        result = await service.validate_for_activation(campaign_id)
        return ValidationResultResponse(
            is_valid=result.is_valid,
            errors=[
                {"field": e.field, "message": e.message, "code": e.code}
                for e in result.errors
            ],
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

@router.post(
    "/{campaign_id}/activate",
    response_model=ActivationResponse,
    summary="Activate campaign",
    description="Validate and activate a campaign, transitioning to running status",
)
async def activate_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
) -> ActivationResponse:
    """Activate a campaign after validation."""
    try:
        campaign = await service.activate_campaign(campaign_id)
        logger.info(
            "Campaign activated via API",
            extra={"campaign_id": str(campaign_id), "user_id": str(current_user.id)},
        )
        return ActivationResponse(
            campaign_id=campaign.id,
            status=campaign.status,
            message="Campaign activated successfully",
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )