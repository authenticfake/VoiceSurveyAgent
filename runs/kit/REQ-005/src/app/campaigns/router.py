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

async def get_validation_service(db: DbSession) -> CampaignValidationService:
    """Dependency to get validation service instance."""
    repository = CampaignRepository(db)
    return CampaignValidationService(repository)

CampaignServiceDep = Annotated[CampaignService, Depends(get_campaign_service)]
ValidationServiceDep = Annotated[CampaignValidationService, Depends(get_validation_service)]

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
) -> CampaignResponse:
    """Create a new campaign."""
    require_role(current_user, [UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER])
    
    campaign = await service.create_campaign(
        data=campaign_data,
        created_by_user_id=current_user.id,
    )
    
    logger.info(
        "Campaign created",
        extra={
            "campaign_id": str(campaign.id),
            "user_id": str(current_user.id),
        },
    )
    
    return CampaignResponse.model_validate(campaign)

@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List campaigns",
    description="Get paginated list of campaigns with optional status filter",
)
async def list_campaigns(
    service: CampaignServiceDep,
    current_user: CurrentUser,
    status_filter: Optional[CampaignStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CampaignListResponse:
    """List campaigns with pagination."""
    campaigns, total = await service.list_campaigns(
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    
    pages = (total + page_size - 1) // page_size
    
    return CampaignListResponse(
        items=[CampaignResponse.model_validate(c) for c in campaigns],
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
    description="Update campaign fields (restricted by current status)",
)
async def update_campaign(
    campaign_id: UUID,
    campaign_data: CampaignUpdate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Update campaign."""
    require_role(current_user, [UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER])
    
    try:
        campaign = await service.update_campaign(campaign_id, campaign_data)
        
        logger.info(
            "Campaign updated",
            extra={
                "campaign_id": str(campaign_id),
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

@router.patch(
    "/{campaign_id}/status",
    response_model=CampaignResponse,
    summary="Update campaign status",
    description="Update campaign status following state machine rules",
)
async def update_campaign_status(
    campaign_id: UUID,
    status_update: CampaignStatusUpdate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Update campaign status."""
    require_role(current_user, [UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER])
    
    try:
        campaign = await service.update_status(campaign_id, status_update.status)
        
        logger.info(
            "Campaign status updated",
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
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete campaign",
    description="Soft delete campaign by setting status to cancelled",
)
async def delete_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> None:
    """Soft delete campaign."""
    require_role(current_user, [UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER])
    
    try:
        await service.delete_campaign(campaign_id)
        
        logger.info(
            "Campaign deleted",
            extra={
                "campaign_id": str(campaign_id),
                "user_id": str(current_user.id),
            },
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

@router.get(
    "/{campaign_id}/validate",
    response_model=ValidationResultResponse,
    summary="Validate campaign for activation",
    description="Check if campaign meets all requirements for activation",
)
async def validate_campaign(
    campaign_id: UUID,
    validation_service: ValidationServiceDep,
    current_user: CurrentUser,
) -> ValidationResultResponse:
    """Validate campaign configuration."""
    require_role(current_user, [UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER])
    
    try:
        result = await validation_service.validate_for_activation(campaign_id)
        return ValidationResultResponse(
            is_valid=result.is_valid,
            errors=result.errors,
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
    description="Validate and activate campaign, transitioning to running status",
)
async def activate_campaign(
    campaign_id: UUID,
    validation_service: ValidationServiceDep,
    current_user: CurrentUser,
) -> ActivationResponse:
    """Activate campaign after validation."""
    require_role(current_user, [UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER])
    
    try:
        await validation_service.activate_campaign(campaign_id)
        
        logger.info(
            "Campaign activated",
            extra={
                "campaign_id": str(campaign_id),
                "user_id": str(current_user.id),
            },
        )
        
        return ActivationResponse(
            campaign_id=campaign_id,
            status=CampaignStatus.RUNNING,
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
            detail={
                "message": e.message,
                "errors": e.details.get("errors", []) if e.details else [],
            },
        )

@router.post(
    "/{campaign_id}/pause",
    response_model=CampaignResponse,
    summary="Pause campaign",
    description="Pause a running campaign",
)
async def pause_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Pause a running campaign."""
    require_role(current_user, [UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER])
    
    try:
        campaign = await service.update_status(campaign_id, CampaignStatus.PAUSED)
        
        logger.info(
            "Campaign paused",
            extra={
                "campaign_id": str(campaign_id),
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