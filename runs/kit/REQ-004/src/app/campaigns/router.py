"""Campaign API router."""

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
)
from app.campaigns.service import CampaignService
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
    dependencies=[Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
)
async def create_campaign(
    data: CampaignCreate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Create a new campaign."""
    campaign = await service.create_campaign(data, current_user.id)
    logger.info(
        "Campaign created via API",
        extra={
            "campaign_id": str(campaign.id),
            "user_id": str(current_user.id),
        }
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
    status_filter: Optional[CampaignStatus] = Query(
        None, alias="status", description="Filter by campaign status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> CampaignListResponse:
    """List campaigns with pagination."""
    campaigns, total = await service.list_campaigns(
        status=status_filter,
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
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update campaign",
    description="Update campaign fields (only allowed in draft/scheduled status)",
    dependencies=[Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
)
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Update campaign fields."""
    try:
        campaign = await service.update_campaign(campaign_id, data)
        logger.info(
            "Campaign updated via API",
            extra={
                "campaign_id": str(campaign_id),
                "user_id": str(current_user.id),
            }
        )
        return CampaignResponse.model_validate(campaign)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{campaign_id}/status",
    response_model=CampaignResponse,
    summary="Update campaign status",
    description="Update campaign status following state machine rules",
    dependencies=[Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
)
async def update_campaign_status(
    campaign_id: UUID,
    data: CampaignStatusUpdate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Update campaign status."""
    try:
        campaign = await service.update_status(campaign_id, data.status)
        logger.info(
            "Campaign status updated via API",
            extra={
                "campaign_id": str(campaign_id),
                "new_status": data.status.value,
                "user_id": str(current_user.id),
            }
        )
        return CampaignResponse.model_validate(campaign)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except StateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Delete campaign",
    description="Soft delete a campaign by setting status to cancelled",
    dependencies=[Depends(require_role(UserRole.CAMPAIGN_MANAGER))],
)
async def delete_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Soft delete a campaign."""
    try:
        campaign = await service.delete_campaign(campaign_id)
        logger.info(
            "Campaign deleted via API",
            extra={
                "campaign_id": str(campaign_id),
                "user_id": str(current_user.id),
            }
        )
        return CampaignResponse.model_validate(campaign)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except StateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))