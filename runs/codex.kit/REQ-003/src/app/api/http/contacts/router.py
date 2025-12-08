from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.auth.dependencies import get_current_user, require_roles
from app.auth.domain.models import Role, UserPrincipal
from app.contacts.domain.enums import ContactState
from app.contacts.domain.errors import ContactCsvValidationError, ContactImportFailedError
from app.contacts.persistence.repository import ContactFilters, Pagination
from app.contacts.services.dependencies import get_contact_service
from app.contacts.services.interfaces import ContactListParams, ContactServiceProtocol

from .schemas import ContactListResponse, ContactUploadResponse, PaginationMetadata, ContactListItem

router = APIRouter(prefix="/api/campaigns/{campaign_id}/contacts", tags=["contacts"])


@router.post(
    "/upload",
    response_model=ContactUploadResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(Role.admin, Role.campaign_manager))],
)
async def upload_contacts(
    campaign_id: UUID,
    file: UploadFile = File(...),
    service: ContactServiceProtocol = Depends(get_contact_service),
    _: UserPrincipal = Depends(get_current_user),
) -> ContactUploadResponse:
    try:
        result = service.import_contacts(campaign_id, file.file)
        return ContactUploadResponse(**result.__dict__)
    except ContactCsvValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "csv_invalid", "message": str(exc)},
        ) from exc
    except ContactImportFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "contact_import_failed", "message": str(exc)},
        ) from exc


@router.get(
    "",
    response_model=ContactListResponse,
    dependencies=[Depends(require_roles(Role.viewer, Role.campaign_manager, Role.admin))],
)
async def list_contacts(
    campaign_id: UUID,
    state: Optional[ContactState] = None,
    page: int = 1,
    page_size: int = 20,
    service: ContactServiceProtocol = Depends(get_contact_service),
    _: UserPrincipal = Depends(get_current_user),
) -> ContactListResponse:
    params = ContactListParams(
        campaign_id=campaign_id,
        filters=ContactFilters(state=state),
        pagination=Pagination(page=page, page_size=page_size),
    )
    page_data = service.list_contacts(params)
    return ContactListResponse(
        data=[ContactListItem.from_domain(record) for record in page_data.contacts],
        pagination=PaginationMetadata(page=page_data.page, page_size=page_data.page_size, total=page_data.total),
    )