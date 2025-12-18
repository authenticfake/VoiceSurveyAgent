"""
Contact API router.

REQ-006: Contact CSV upload and parsing
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import CurrentUser, get_current_user
from app.auth.rbac import require_campaign_manager
from app.contacts.models import ContactState
from app.contacts.schemas import (
    ContactListResponse,
    ContactResponse,
    CSVUploadResponse,
)
from app.contacts.service import ContactService
from app.shared.database import get_db_session
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["contacts"])


def get_contact_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContactService:
    """Dependency for contact service."""
    return ContactService(session=session)


@router.post(
    "/{campaign_id}/contacts/upload",
    response_model=CSVUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload contacts CSV",
    description="Upload a CSV file of contacts for a campaign. Campaign must be in draft status.",
)
async def upload_contacts_csv(
    campaign_id: UUID,
    file: Annotated[UploadFile, File(description="CSV file with contacts")],
    service: Annotated[ContactService, Depends(get_contact_service)],
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    delimiter: Annotated[str, Query(max_length=1)] = ",",
    encoding: Annotated[str, Query(max_length=20)] = "utf-8",
) -> CSVUploadResponse:
    """Upload contacts from a CSV file.

    The CSV file must contain at minimum a 'phone_number' column.
    Optional columns: external_contact_id, email, language, has_prior_consent, do_not_call.

    Phone numbers must be in E.164 format (e.g., +14155551234).

    Args:
        campaign_id: Campaign UUID.
        file: CSV file upload.
        service: Contact service.
        current_user: Authenticated user.
        delimiter: CSV field delimiter (default: comma).
        encoding: File encoding (default: utf-8).

    Returns:
        Upload result with accepted/rejected counts and errors.

    Raises:
        404: Campaign not found.
        400: Campaign not in draft status or invalid CSV.
    """
    logger.info(
        "CSV upload started",
        extra={
            "campaign_id": str(campaign_id),
            "user_id": str(current_user.id),
            "filename": file.filename,
            "content_type": file.content_type,
        },
    )

    # Read file content
    content = await file.read()

    if not content:
        raise ValidationError("Empty file uploaded")

    # Process CSV
    result = await service.upload_csv(
        campaign_id=campaign_id,
        content=content,
        delimiter=delimiter,
        encoding=encoding,
    )

    logger.info(
        "CSV upload completed",
        extra={
            "campaign_id": str(campaign_id),
            "user_id": str(current_user.id),
            "accepted_count": result.accepted_count,
            "rejected_count": result.rejected_count,
            "acceptance_rate": result.acceptance_rate,
        },
    )

    return result


@router.get(
    "/{campaign_id}/contacts",
    response_model=ContactListResponse,
    summary="List campaign contacts",
    description="Get paginated list of contacts for a campaign.",
)
async def list_contacts(
    campaign_id: UUID,
    service: Annotated[ContactService, Depends(get_contact_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    state: Annotated[ContactState | None, Query()] = None,
) -> ContactListResponse:
    """List contacts for a campaign.

    Args:
        campaign_id: Campaign UUID.
        service: Contact service.
        current_user: Authenticated user.
        page: Page number (1-indexed).
        page_size: Number of items per page (max 100).
        state: Optional state filter.

    Returns:
        Paginated contact list.

    Raises:
        404: Campaign not found.
    """
    return await service.get_contacts(
        campaign_id=campaign_id,
        page=page,
        page_size=page_size,
        state=state,
    )


@router.get(
    "/{campaign_id}/contacts/{contact_id}",
    response_model=ContactResponse,
    summary="Get contact details",
    description="Get details of a specific contact.",
)
async def get_contact(
    campaign_id: UUID,
    contact_id: UUID,
    service: Annotated[ContactService, Depends(get_contact_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ContactResponse:
    """Get a specific contact.

    Args:
        campaign_id: Campaign UUID (for URL consistency).
        contact_id: Contact UUID.
        service: Contact service.
        current_user: Authenticated user.

    Returns:
        Contact details.

    Raises:
        404: Contact not found.
    """
    contact = await service.get_contact(contact_id)

    # Verify contact belongs to the campaign
    if contact.campaign_id != campaign_id:
        raise NotFoundError(f"Contact {contact_id} not found in campaign {campaign_id}")

    return contact