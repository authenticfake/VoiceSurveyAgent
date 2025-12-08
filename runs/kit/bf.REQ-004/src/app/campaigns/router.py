"""
Campaign API router.

Defines REST endpoints for campaign CRUD operations.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.rbac import CampaignManagerUser, ViewerUser
from app.auth.schemas import UserContext
from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import (
    CampaignCreate,
    CampaignListResponse,
    CampaignResponse,
    CampaignStatus,
    CampaignUpdate,
    StatusTransitionRequest,
)
from app.campaigns.service import CampaignService
from app.config import get_settings
from app.shared.database import DbSession
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

def get_campaign_service(db: DbSession) -> CampaignService:
    """Dependency to get campaign service instance."""
    repository = CampaignRepository(db)
    return CampaignService(repository)

CampaignServiceDep = Annotated[CampaignService, Depends(get_campaign_service)]

@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new campaign",
    description="Creates a new campaign in draft status. Requires campaign_manager or admin role.",
)
async def create_campaign(
    data: CampaignCreate,
    service: CampaignServiceDep,
    user: CampaignManagerUser,
) -> CampaignResponse:
    """Create a new campaign."""
    campaign = await service.create_campaign(data, user)
    return CampaignResponse.model_validate(campaign)

@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List campaigns",
    description="Returns a paginated list of campaigns with optional status filter.",
)
async def list_campaigns(
    service: CampaignServiceDep,
    user: ViewerUser,
    status_filter: Annotated[
        CampaignStatus | None,
        Query(alias="status", description="Filter by campaign status"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page"),
    ] = None,
) -> CampaignListResponse:
    """List campaigns with pagination."""
    if page_size is None:
        page_size = settings.default_page_size

    campaigns, total = await service.list_campaigns(
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

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
    description="Returns full details of a specific campaign.",
)
async def get_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    user: ViewerUser,
) -> CampaignResponse:
    """Get campaign by ID."""
    campaign = await service.get_campaign(campaign_id)
    return CampaignResponse.model_validate(campaign)

@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update campaign",
    description="Updates campaign fields. Allowed fields depend on current status.",
)
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    service: CampaignServiceDep,
    user: CampaignManagerUser,
) -> CampaignResponse:
    """Update campaign."""
    campaign = await service.update_campaign(campaign_id, data, user)
    return CampaignResponse.model_validate(campaign)

@router.delete(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Delete campaign",
    description="Soft deletes a campaign by setting status to cancelled.",
)
async def delete_campaign(
    campaign_id: UUID,
    service: CampaignServiceDep,
    user: CampaignManagerUser,
) -> CampaignResponse:
    """Soft delete campaign."""
    campaign = await service.delete_campaign(campaign_id, user)
    return CampaignResponse.model_validate(campaign)

@router.post(
    "/{campaign_id}/status",
    response_model=CampaignResponse,
    summary="Transition campaign status",
    description="Transitions campaign to a new status following the state machine rules.",
)
async def transition_campaign_status(
    campaign_id: UUID,
    request: StatusTransitionRequest,
    service: CampaignServiceDep,
    user: CampaignManagerUser,
) -> CampaignResponse:
    """Transition campaign status."""
    campaign = await service.transition_status(campaign_id, request.target_status, user)
    return CampaignResponse.model_validate(campaign)