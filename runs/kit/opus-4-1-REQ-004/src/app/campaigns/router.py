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
    summary="Create campaign",
    description="Create a new campaign in draft status",
    dependencies=[Depends(require_role([UserRole.CAMPAIGN_MANAGER, UserRole.ADMIN]))],
)
async def create_campaign(
    campaign_data: CampaignCreate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Create a new campaign."""
    try:
        campaign = await service.create_campaign(
            data=campaign_data,
            user_id=current_user.id,
        )
        logger.info(f"User {current_user.id} created campaign {campaign.id}")
        return campaign
    except Exception as e:
        logger.error(f"Failed to create campaign: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create campaign",
        )


@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List campaigns",
    description="Get paginated list of campaigns with optional status filter",
)
async def list_campaigns(
    service: CampaignServiceDep,
    current_user: CurrentUser,
    status: Optional[CampaignStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> CampaignListResponse:
    """Get paginated list of campaigns."""
    try:
        # Viewers can only see campaigns, not filter by user
        user_filter = None
        if current_user.role == UserRole.VIEWER:
            user_filter = None
        
        campaigns = await service.list_campaigns(
            status=status,
            user_id=user_filter,
            page=page,
            page_size=page_size,
        )
        return campaigns
    except Exception as e:
        logger.error(f"Failed to list campaigns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list campaigns",
        )


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get campaign",
    description="Get campaign details by ID",
)
async def get_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Get campaign by ID."""
    try:
        campaign = await service.get_campaign(campaign_id)
        return campaign
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get campaign {campaign_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get campaign",
        )


@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update campaign",
    description="Update campaign fields (only allowed in draft or paused status)",
    dependencies=[Depends(require_role([UserRole.CAMPAIGN_MANAGER, UserRole.ADMIN]))],
)
async def update_campaign(
    campaign_id: UUID,
    campaign_data: CampaignUpdate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Update campaign."""
    try:
        campaign = await service.update_campaign(
            campaign_id=campaign_id,
            data=campaign_data,
        )
        logger.info(f"User {current_user.id} updated campaign {campaign_id}")
        return campaign
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update campaign {campaign_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update campaign",
        )


@router.post(
    "/{campaign_id}/status",
    response_model=CampaignResponse,
    summary="Update campaign status",
    description="Transition campaign to new status following state machine rules",
    dependencies=[Depends(require_role([UserRole.CAMPAIGN_MANAGER, UserRole.ADMIN]))],
)
async def update_campaign_status(
    campaign_id: UUID,
    status_update: CampaignStatusUpdate,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    """Update campaign status."""
    try:
        campaign = await service.transition_status(
            campaign_id=campaign_id,
            new_status=status_update.status,
        )
        logger.info(
            f"User {current_user.id} changed campaign {campaign_id} status to {status_update.status}"
        )
        return campaign
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update campaign {campaign_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update campaign status",
        )


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete campaign",
    description="Soft delete campaign (sets status to cancelled)",
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
async def delete_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> None:
    """Delete campaign."""
    try:
        deleted = await service.delete_campaign(campaign_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )
        logger.info(f"User {current_user.id} deleted campaign {campaign_id}")
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to delete campaign {campaign_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete campaign",
        )