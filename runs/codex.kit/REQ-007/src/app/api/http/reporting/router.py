from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.http.reporting.schemas import (
    CampaignStatsResponse,
    ContactListQuery,
    ContactListResponse,
    ContactSummaryModel,
    PaginationMetadata,
)
from app.auth.dependencies import get_current_user, require_roles
from app.auth.domain.models import Role
from app.reporting.exceptions import CampaignNotFoundError
from app.reporting.services import ReportingService
from app.reporting.value_objects import ContactListFilters

try:  # pragma: no cover - dependency holder
    from app.infra.db.dependencies import get_db_session as get_db_session_dependency
except ImportError:  # pragma: no cover - defensive fallback
    def get_db_session_dependency() -> Session:
        raise RuntimeError("Database session dependency is not wired.")


router = APIRouter(prefix="/api/campaigns/{campaign_id}", tags=["reporting"])

viewer_role_guard = require_roles(Role.viewer, Role.campaign_manager, Role.admin)
manager_role_guard = require_roles(Role.campaign_manager, Role.admin)


def get_reporting_service(
    session: Annotated[Session, Depends(get_db_session_dependency)],
) -> ReportingService:
    return ReportingService(session)


@router.get(
    "/stats",
    response_model=CampaignStatsResponse,
    dependencies=[Depends(viewer_role_guard), Depends(get_current_user)],
)
def get_campaign_stats(
    campaign_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
) -> CampaignStatsResponse:
    try:
        stats = service.get_campaign_stats(campaign_id)
    except CampaignNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return CampaignStatsResponse(**stats.__dict__)


@router.get(
    "/contacts",
    response_model=ContactListResponse,
    dependencies=[Depends(viewer_role_guard), Depends(get_current_user)],
)
def list_campaign_contacts(
    campaign_id: UUID,
    query: ContactListQuery = Depends(),
    service: ReportingService = Depends(get_reporting_service),
) -> ContactListResponse:
    filters = ContactListFilters(
        state=query.state,
        last_outcome=query.last_outcome,
        page=query.page,
        page_size=query.page_size,
        sort_desc=(query.sort == "recent"),
    )

    try:
        result = service.list_contacts(campaign_id, filters)
    except CampaignNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return ContactListResponse(
        items=[
            ContactSummaryModel(
                contact_id=item.contact_id,
                external_contact_id=item.external_contact_id,
                phone_number=item.phone_number,
                email=item.email,
                state=item.state,
                attempts_count=item.attempts_count,
                last_outcome=item.last_outcome,
                last_attempt_at=item.last_attempt_at,
                updated_at=item.updated_at,
            )
            for item in result.items
        ],
        pagination=PaginationMetadata(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
        ),
    )


@router.get(
    "/export",
    response_class=StreamingResponse,
    dependencies=[Depends(manager_role_guard), Depends(get_current_user)],
)
def export_campaign_contacts_csv(
    campaign_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
) -> StreamingResponse:
    try:
        stream = service.iter_contacts_csv(campaign_id)
    except CampaignNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="campaign-{campaign_id}-contacts.csv"'
        },
    )