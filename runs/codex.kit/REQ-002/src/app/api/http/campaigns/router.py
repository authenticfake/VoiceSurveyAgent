from __future__ import annotations

import logging
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user, require_roles
from app.auth.domain.models import Role, UserPrincipal
from app.campaigns.domain.errors import (
    CampaignActivationError,
    CampaignNotFoundError,
    CampaignStatusError,
    CampaignValidationError,
)
from app.campaigns.domain.models import CampaignRecord
from app.campaigns.services.dependencies import get_campaign_service
from app.campaigns.services.interfaces import CampaignFilters, PaginationParams
from app.campaigns.services.service import CampaignService

from .schemas import (
    CallWindowModel,
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignQuestionModel,
    CampaignResponse,
    CampaignUpdateRequest,
    EmailTemplatesModel,
    PaginationMetadata,
    RetryPolicyModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _to_question_models(record: CampaignRecord) -> List[CampaignQuestionModel]:
    return [
        CampaignQuestionModel(text=question.text, answer_type=question.answer_type)
        for question in sorted(record.questions, key=lambda q: q.position)
    ]


def _to_retry_policy_model(record: CampaignRecord) -> RetryPolicyModel:
    return RetryPolicyModel(
        max_attempts=record.retry_policy.max_attempts,
        retry_interval_minutes=record.retry_policy.retry_interval_minutes,
    )


def _to_call_window_model(record: CampaignRecord) -> CallWindowModel:
    return CallWindowModel(
        start_local=record.call_window.start_local,
        end_local=record.call_window.end_local,
    )


def _to_email_templates_model(record: CampaignRecord) -> EmailTemplatesModel:
    return EmailTemplatesModel(
        completed_template_id=record.email_templates.completed_template_id,
        refused_template_id=record.email_templates.refused_template_id,
        not_reached_template_id=record.email_templates.not_reached_template_id,
    )


def _to_campaign_response(record: CampaignRecord) -> CampaignResponse:
    return CampaignResponse(
        id=record.id,
        name=record.name,
        description=record.description,
        status=record.status,
        language=record.language,
        intro_script=record.intro_script,
        questions=_to_question_models(record),
        retry_policy=_to_retry_policy_model(record),
        allowed_call_window=_to_call_window_model(record),
        email_templates=_to_email_templates_model(record),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.admin, Role.campaign_manager))],
)
def create_campaign(
    payload: CampaignCreateRequest,
    user: UserPrincipal = Depends(get_current_user),
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignResponse:
    try:
        campaign = service.create_campaign(payload.to_command(), user)
        return _to_campaign_response(campaign)
    except CampaignValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "campaign_validation_error", "message": str(exc)},
        ) from exc


@router.get(
    "",
    response_model=CampaignListResponse,
    dependencies=[Depends(require_roles(Role.viewer, Role.campaign_manager, Role.admin))],
)
def list_campaigns(
    status: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignListResponse:
    filters = CampaignFilters(
        status=status,
        created_from=created_from,
        created_to=created_to,
    )
    pagination = PaginationParams(page=page, page_size=page_size)
    result = service.list_campaigns(filters, pagination)
    response = CampaignListResponse(
        items=[_to_campaign_response(item) for item in result.items],
        pagination=PaginationMetadata(
            page=result.pagination.page,
            page_size=result.pagination.page_size,
            total_items=result.pagination.total_items,
            total_pages=result.pagination.total_pages,
        ),
    )
    return response


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    dependencies=[Depends(require_roles(Role.viewer, Role.campaign_manager, Role.admin))],
)
def get_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignResponse:
    try:
        campaign = service.get_campaign(campaign_id)
        return _to_campaign_response(campaign)
    except CampaignNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "campaign_not_found", "message": str(exc)},
        ) from exc


@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    dependencies=[Depends(require_roles(Role.admin, Role.campaign_manager))],
)
def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdateRequest,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignResponse:
    try:
        campaign = service.update_campaign(campaign_id, payload.to_command())
        return _to_campaign_response(campaign)
    except CampaignValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "campaign_validation_error", "message": str(exc)},
        ) from exc
    except CampaignNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "campaign_not_found", "message": str(exc)},
        ) from exc
    except CampaignStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "campaign_status_error", "message": str(exc)},
        ) from exc


@router.post(
    "/{campaign_id}/activate",
    response_model=CampaignResponse,
    dependencies=[Depends(require_roles(Role.admin, Role.campaign_manager))],
)
def activate_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignResponse:
    try:
        campaign = service.activate_campaign(campaign_id)
        return _to_campaign_response(campaign)
    except (CampaignValidationError, CampaignActivationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "campaign_activation_error", "message": str(exc)},
        ) from exc
    except CampaignStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "campaign_status_error", "message": str(exc)},
        ) from exc
    except CampaignNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "campaign_not_found", "message": str(exc)},
        ) from exc


@router.post(
    "/{campaign_id}/pause",
    response_model=CampaignResponse,
    dependencies=[Depends(require_roles(Role.admin, Role.campaign_manager))],
)
def pause_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignResponse:
    try:
        campaign = service.pause_campaign(campaign_id)
        return _to_campaign_response(campaign)
    except CampaignStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "campaign_status_error", "message": str(exc)},
        ) from exc
    except CampaignNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "campaign_not_found", "message": str(exc)},
        ) from exc