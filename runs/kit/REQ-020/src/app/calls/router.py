"""
Call detail API router for REQ-020.

Provides GET /api/calls/{call_id} endpoint.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.calls.exceptions import CallAccessDeniedError, CallNotFoundError
from app.calls.models import CallDetailResponse
from app.calls.service import CallDetailService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["calls"])


# Dependency stubs - these would be provided by the auth module (REQ-002/REQ-003)
class CurrentUser:
    """Represents the current authenticated user."""
    
    def __init__(self, user_id: UUID, role: str):
        self.user_id = user_id
        self.role = role


async def get_current_user() -> CurrentUser:
    """Dependency to get current authenticated user.
    
    This is a stub - actual implementation comes from REQ-002.
    In tests, this will be overridden.
    """
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


async def require_campaign_manager_or_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
) -> CurrentUser:
    """Dependency to require campaign_manager or admin role.
    
    This is a stub - actual implementation comes from REQ-003.
    """
    if current_user.role not in ("campaign_manager", "admin"):
        logger.warning(
            "Access denied for user %s with role %s to call detail endpoint",
            current_user.user_id,
            current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to campaign_manager and admin roles",
        )
    return current_user


async def get_call_detail_service() -> CallDetailService:
    """Dependency to get CallDetailService.
    
    This is a stub - actual implementation would inject the repository.
    In tests, this will be overridden.
    """
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Service not configured",
    )


@router.get(
    "/{call_id}",
    response_model=CallDetailResponse,
    summary="Get call details",
    description="Retrieve detailed information about a specific call attempt.",
    responses={
        200: {"description": "Call details retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied - requires campaign_manager or admin role"},
        404: {"description": "Call not found"},
    },
)
async def get_call_detail(
    call_id: str,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager_or_admin)],
    service: Annotated[CallDetailService, Depends(get_call_detail_service)],
) -> CallDetailResponse:
    """Get detailed information about a call.
    
    Args:
        call_id: The internal call identifier
        current_user: The authenticated user (injected)
        service: The call detail service (injected)
    
    Returns:
        CallDetailResponse with full call information
    
    Raises:
        HTTPException 404: If call_id doesn't exist
        HTTPException 403: If user doesn't have required role
        HTTPException 401: If not authenticated
    """
    try:
        return await service.get_call_detail(
            call_id=call_id,
            user_id=current_user.user_id,
        )
    except CallNotFoundError:
        logger.info("Call not found: %s", call_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call not found: {call_id}",
        )
    except CallAccessDeniedError as e:
        logger.warning(
            "Access denied to call %s for user %s: %s",
            call_id,
            current_user.user_id,
            e.reason,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.reason,
        )