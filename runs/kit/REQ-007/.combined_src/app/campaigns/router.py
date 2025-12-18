"""
Campaign API router.

REQ-004: Campaign CRUD API
"""

import math
from typing import Annotated
from uuid import UUID
import inspect

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Callable, Optional, get_args, get_origin
from fastapi.params import Depends as DependsParam
import inspect

from app.auth.middleware import CurrentUser
from app.auth.rbac import require_campaign_manager, require_viewer, RBACChecker
from app.campaigns.models import CampaignStatus
from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import (
    CampaignCreate,
    CampaignListResponse,
    CampaignListItem,
    CampaignResponse,
    CampaignStatusTransition,
    CampaignUpdate,
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
)
from app.campaigns.service import CampaignService
from app.shared.database import get_db_session
from app.shared.exceptions import (
    CampaignNotFoundError,
    InvalidStatusTransitionError,
    ValidationError,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def get_campaign_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignService:
    """Dependency for campaign service."""
    repository = CampaignRepository(session)
    return CampaignService(repository)

def _extract_session_dependency() -> Optional[Callable[..., Any]]:
    """
    Try to extract the dependency callable used to provide the `session` argument
    for get_campaign_service, so we can depend on it in our indirection wrapper.
    Supports both:
      - session: Annotated[AsyncSession, Depends(get_db_session)]
      - session: AsyncSession = Depends(get_db_session)
    """
    try:
        sig = inspect.signature(get_campaign_service)
        param = sig.parameters.get("session")
        if param is None:
            return None

        # Pattern: session: AsyncSession = Depends(get_db_session)
        default = param.default
        if default is not inspect._empty and hasattr(default, "dependency"):
            return default.dependency  # type: ignore[attr-defined]

        # Pattern: session: Annotated[AsyncSession, Depends(get_db_session)]
        ann = param.annotation
        if get_origin(ann) is not None and get_origin(ann).__name__ == "Annotated":
            for meta in get_args(ann)[1:]:
                if isinstance(meta, DependsParam) and getattr(meta, "dependency", None):
                    return meta.dependency
    except Exception:
        return None

    return None


_SESSION_DEP = _extract_session_dependency()


if _SESSION_DEP is None:
    # Fallback: keep old behavior (but ideally _SESSION_DEP should be found)
    async def _campaign_service_dep() -> CampaignService:
        maybe = get_campaign_service()  # may still fail if session is required
        if inspect.isawaitable(maybe):
            return await maybe
        return maybe
else:
    async def _campaign_service_dep(session: Any = Depends(_SESSION_DEP)) -> CampaignService:
        """
        Indirection dependency so tests can patch `app.campaigns.router.get_campaign_service`
        and FastAPI will still inject the DB session correctly.
        """
        maybe = get_campaign_service(session)
        if inspect.isawaitable(maybe):
            return await maybe
        return maybe


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Campaign created successfully"},
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def create_campaign(
    data: CampaignCreate,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    service: Annotated[CampaignService, Depends(_campaign_service_dep)],
) -> CampaignResponse:
    """Create a new campaign.

    Creates a new campaign in draft status. Only users with campaign_manager
    or admin role can create campaigns.
    """
    logger.info(
        "Creating campaign",
        extra={
            "user_id": str(current_user.id),
            "campaign_name": data.name,
        },
    )

    campaign = await service.create_campaign(
        data=data,
        created_by_user_id=current_user.id,
    )

    return CampaignResponse.model_validate(campaign)


@router.get(
    "",
    response_model=CampaignListResponse,
    responses={
        200: {"description": "Campaign list retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def list_campaigns(
    current_user: Annotated[CurrentUser, Depends(require_viewer)],
    service: Annotated[CampaignService, Depends(_campaign_service_dep)],
    status_filter: Annotated[
        CampaignStatus | None,
        Query(alias="status", description="Filter by campaign status"),
    ] = None,
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)"),
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page"),
    ] = 20,
) -> CampaignListResponse:
    """Get paginated list of campaigns.

    Returns a paginated list of campaigns with optional status filter.
    All authenticated users can view campaigns.
    """
    campaigns, total = await service.list_campaigns(
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return CampaignListResponse(
        items=[CampaignListItem.model_validate(c) for c in campaigns],
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    responses={
        200: {"description": "Campaign retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Campaign not found"},
    },
)
async def get_campaign(
    campaign_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_viewer)],
    service: Annotated[CampaignService, Depends(_campaign_service_dep)],
) -> CampaignResponse:
    """Get campaign details by ID.

    Returns full campaign details. All authenticated users can view campaigns.
    """
    try:
        campaign = await service.get_campaign(campaign_id)
        return CampaignResponse.model_validate(campaign)
    except CampaignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CAMPAIGN_NOT_FOUND",
                "message": f"Campaign with ID {campaign_id} not found",
            },
        )


@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    responses={
        200: {"description": "Campaign updated successfully"},
        400: {"model": ErrorResponse, "description": "Validation error or invalid update"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Campaign not found"},
    },
)
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    service: Annotated[CampaignService, Depends(_campaign_service_dep)],
    ) -> CampaignResponse:
    """Update an existing campaign.

    Updates campaign fields. Some fields can only be updated when campaign
    is in draft status. Only users with campaign_manager or admin role can
    update campaigns.
    """
    logger.info(
        "Updating campaign",
        extra={
            "user_id": str(current_user.id),
            "campaign_id": str(campaign_id),
        },
    )

    try:
        campaign = await service.update_campaign(campaign_id, data)
        return CampaignResponse.model_validate(campaign)
    except CampaignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CAMPAIGN_NOT_FOUND",
                "message": f"Campaign with ID {campaign_id} not found",
            },
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(e),
            },
        )


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Campaign deleted successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Campaign not found"},
    },
)
async def delete_campaign(
    campaign_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    service: Annotated[CampaignService, Depends(_campaign_service_dep)],
) -> None:
    """Delete a campaign (soft delete).

    Sets campaign status to cancelled. Only users with campaign_manager
    or admin role can delete campaigns.
    """
    logger.info(
        "Deleting campaign",
        extra={
            "user_id": str(current_user.id),
            "campaign_id": str(campaign_id),
        },
    )

    try:
        await service.delete_campaign(campaign_id)
    except CampaignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CAMPAIGN_NOT_FOUND",
                "message": f"Campaign with ID {campaign_id} not found",
            },
        )


@router.post(
    "/{campaign_id}/status",
    response_model=CampaignResponse,
    responses={
        200: {"description": "Status transitioned successfully"},
        400: {"model": ErrorResponse, "description": "Invalid status transition"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Campaign not found"},
    },
)
async def transition_campaign_status(
    campaign_id: UUID,
    data: CampaignStatusTransition,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    service:Annotated[CampaignService, Depends(_campaign_service_dep)],
) -> CampaignResponse:
    """Transition campaign to a new status.

    Transitions campaign status following the state machine:
    draft → scheduled → running → paused → completed
    
    Only users with campaign_manager or admin role can transition status.
    """
    logger.info(
        "Transitioning campaign status",
        extra={
            "user_id": str(current_user.id),
            "campaign_id": str(campaign_id),
            "target_status": data.status.value,
        },
    )

    try:
        campaign = await service.transition_status(campaign_id, data.status)
        return CampaignResponse.model_validate(campaign)
    except CampaignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CAMPAIGN_NOT_FOUND",
                "message": f"Campaign with ID {campaign_id} not found",
            },
        )
    except InvalidStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STATUS_TRANSITION",
                "message": str(e),
                "current_status": e.current_status.value,
                "target_status": e.target_status.value,
                "valid_transitions": [s.value for s in e.valid_transitions],
            },
        )