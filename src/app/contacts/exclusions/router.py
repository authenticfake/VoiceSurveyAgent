"""
API router for exclusion list management.

REQ-007: Exclusion list management
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import CurrentUser, get_current_user
from app.contacts.exclusions.models import ExclusionSource
from app.contacts.exclusions.schemas import (
    ExclusionCreateRequest,
    ExclusionEntryResponse,
    ExclusionImportResponse,
    ExclusionListResponse,
)
from app.contacts.exclusions.service import ExclusionService
from app.shared.database import get_db_session
from app.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/exclusions", tags=["exclusions"])


def _forbidden(detail: str = "Insufficient permissions") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def require_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if getattr(current_user, "role", None) != "admin":
        raise _forbidden("Admin role required")
    return current_user


async def require_campaign_manager_or_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    role = getattr(current_user, "role", None)
    if role not in {"admin", "campaign_manager"}:
        raise _forbidden("Campaign manager or admin role required")
    return current_user


def get_exclusion_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExclusionService:
    """Dependency for exclusion service."""
    return ExclusionService(session=session)


@router.post(
    "/import",
    response_model=ExclusionImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import exclusion list from CSV",
    description="Import phone numbers to exclusion list from CSV file. "
    "CSV must have 'phone_number' or 'phone' column. "
    "Optional 'reason' column for exclusion reason.",
)
async def import_exclusions(
    file: Annotated[UploadFile, File(description="CSV file with phone numbers")],
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager_or_admin)],
    service: Annotated[ExclusionService, Depends(get_exclusion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    reason: Annotated[
        str | None,
        Query(description="Default reason for exclusions if not in CSV"),
    ] = None,
) -> ExclusionImportResponse:
    """Import exclusion entries from CSV file.

    Requires campaign_manager or admin role.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    try:
        result = await service.import_csv(content, reason=reason)
        await session.commit()

        logger.info(
            "Exclusion CSV import completed",
            extra={
                "user_id": str(current_user.id),
                "exclusion_filename": file.filename,
                "accepted": result.accepted_count,
                "rejected": result.rejected_count,
                "duplicates": result.duplicate_count,
            },
        )

        return result
    except Exception as e:
        await session.rollback()
        logger.error(
            "Exclusion CSV import failed",
            extra={
                "user_id": str(current_user.id),
                "exclusion_filename": file.filename,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


@router.post(
    "",
    response_model=ExclusionEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add phone number to exclusion list",
    description="Manually add a single phone number to the exclusion list.",
)
async def create_exclusion(
    request: ExclusionCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager_or_admin)],
    service: Annotated[ExclusionService, Depends(get_exclusion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExclusionEntryResponse:
    """Add a phone number to the exclusion list.

    Requires campaign_manager or admin role.
    """
    try:
        entry = await service.create_exclusion(request, source=ExclusionSource.API)
        await session.commit()

        logger.info(
            "Exclusion entry created via API",
            extra={
                "user_id": str(current_user.id),
                "exclusion_id": str(entry.id),
                "phone_number": entry.phone_number,
            },
        )

        return ExclusionEntryResponse.model_validate(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=ExclusionListResponse,
    summary="List exclusion entries",
    description="Get paginated list of all exclusion entries.",
)
async def list_exclusions(
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager_or_admin)],
    service: Annotated[ExclusionService, Depends(get_exclusion_service)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Items per page")
    ] = 50,
) -> ExclusionListResponse:
    """List all exclusion entries with pagination.

    Requires campaign_manager or admin role.
    """
    entries, total = await service.list_exclusions(page=page, page_size=page_size)

    total_pages = (total + page_size - 1) // page_size

    return ExclusionListResponse(
        items=[ExclusionEntryResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{exclusion_id}",
    response_model=ExclusionEntryResponse,
    summary="Get exclusion entry",
    description="Get a single exclusion entry by ID.",
)
async def get_exclusion(
    exclusion_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager_or_admin)],
    service: Annotated[ExclusionService, Depends(get_exclusion_service)],
) -> ExclusionEntryResponse:
    """Get exclusion entry by ID.

    Requires campaign_manager or admin role.
    """
    entry = await service.get_exclusion(exclusion_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exclusion entry not found",
        )
    return ExclusionEntryResponse.model_validate(entry)


@router.delete(
    "/{exclusion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove exclusion entry",
    description="Remove a phone number from the exclusion list. Requires admin role.",
)
async def delete_exclusion(
    exclusion_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    service: Annotated[ExclusionService, Depends(get_exclusion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Remove an exclusion entry.

    Requires admin role.
    """
    deleted = await service.delete_exclusion(exclusion_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exclusion entry not found",
        )

    await session.commit()

    logger.info(
        "Exclusion entry deleted",
        extra={
            "user_id": str(current_user.id),
            "exclusion_id": str(exclusion_id),
        },
    )


@router.post(
    "/sync-contacts",
    status_code=status.HTTP_200_OK,
    summary="Sync contacts with exclusion list",
    description="Mark contacts as excluded if their phone is in the exclusion list.",
)
async def sync_contacts_with_exclusions(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    service: Annotated[ExclusionService, Depends(get_exclusion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    campaign_id: Annotated[
        UUID | None,
        Query(description="Optional campaign ID to limit scope"),
    ] = None,
) -> dict[str, int]:
    """Sync contacts with exclusion list.

    Marks contacts as excluded if their phone number is in the exclusion list.
    Requires admin role.
    """
    count = await service.mark_contacts_excluded(campaign_id=campaign_id)
    await session.commit()

    logger.info(
        "Contacts synced with exclusion list",
        extra={
            "user_id": str(current_user.id),
            "campaign_id": str(campaign_id) if campaign_id else "all",
            "excluded_count": count,
        },
    )

    return {"excluded_count": count}