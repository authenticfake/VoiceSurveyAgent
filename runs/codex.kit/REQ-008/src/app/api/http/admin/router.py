from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.admin.domain.models import (
    AdminConfigurationUpdateRequest,
    AdminConfigurationView,
)
from app.admin.services.config_service import AdminConfigService
from app.admin.services.dependencies import get_admin_config_service
from app.auth.dependencies import require_roles
from app.auth.domain.models import Role, UserPrincipal

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin_required = require_roles(Role.admin)


@router.get(
    "/config",
    response_model=AdminConfigurationView,
    status_code=status.HTTP_200_OK,
    summary="Retrieve provider, retention, and template configuration.",
)
def get_admin_configuration(
    _: UserPrincipal = Depends(admin_required),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminConfigurationView:
    return service.get_configuration()


@router.put(
    "/config",
    response_model=AdminConfigurationView,
    status_code=status.HTTP_200_OK,
    summary="Update provider configuration, retention settings, and templates.",
)
def update_admin_configuration(
    payload: AdminConfigurationUpdateRequest,
    principal: UserPrincipal = Depends(admin_required),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminConfigurationView:
    return service.update_configuration(payload, principal)