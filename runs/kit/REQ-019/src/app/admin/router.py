"""
Admin configuration API router.

REQ-019: Admin configuration API
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import (
    AdminConfigResponse,
    AdminConfigUpdate,
    AuditLogListResponse,
)
from app.admin.secrets import SecretsManagerInterface, get_secrets_manager
from app.admin.service import AdminConfigService
from app.shared.database import get_db_session
from app.shared.exceptions import AuthorizationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Dependency for getting current user (simplified - would integrate with REQ-002/REQ-003)
async def get_current_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> UUID:
    """
    Extract current user from headers.
    In production, this would validate JWT and extract user info.
    For REQ-019, we use headers for testing; real auth comes from REQ-002/REQ-003.
    """
    if not x_user_id:
        raise AuthorizationError("User ID required")
    if x_user_role != "admin":
        raise AuthorizationError("Admin role required for this endpoint")
    try:
        return UUID(x_user_id)
    except ValueError:
        raise AuthorizationError("Invalid user ID format")


async def get_admin_service(
    session: AsyncSession = Depends(get_db_session),
    secrets_manager: SecretsManagerInterface = Depends(get_secrets_manager),
) -> AdminConfigService:
    """Dependency for admin config service."""
    return AdminConfigService(session=session, secrets_manager=secrets_manager)


@router.get("/config", response_model=AdminConfigResponse)
async def get_config(
    user_id: UUID = Depends(get_current_user_id),
    service: AdminConfigService = Depends(get_admin_service),
    request: Request = None,
) -> AdminConfigResponse:
    """
    Get current admin configuration.

    Returns the current configuration for telephony, LLM, email, and retention settings.
    Credentials are never returned in the response.

    Requires admin role.
    """
    logger.info(f"Admin config read by user: {user_id}")

    # Log the read action
    await service.repository.create_audit_log(
        user_id=user_id,
        action="config.read",
        resource_type="admin_config",
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )

    return await service.get_config()


@router.put("/config", response_model=AdminConfigResponse)
async def update_config(
    update: AdminConfigUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: AdminConfigService = Depends(get_admin_service),
    request: Request = None,
) -> AdminConfigResponse:
    """
    Update admin configuration.

    Updates configuration for telephony, LLM, email, and/or retention settings.
    Credentials are stored securely in AWS Secrets Manager.
    All changes are logged in the audit trail.

    Requires admin role.
    """
    logger.info(f"Admin config update by user: {user_id}")

    return await service.update_config(
        update=update,
        user_id=user_id,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    filter_user_id: Optional[UUID] = Query(None, alias="user_id", description="Filter by user ID"),
    user_id: UUID = Depends(get_current_user_id),
    service: AdminConfigService = Depends(get_admin_service),
) -> AuditLogListResponse:
    """
    Get paginated audit logs.

    Returns audit log entries for configuration changes.
    Can be filtered by resource type and user ID.

    Requires admin role.
    """
    logger.info(f"Audit logs requested by user: {user_id}")

    return await service.get_audit_logs(
        page=page,
        page_size=page_size,
        resource_type=resource_type,
        user_id=filter_user_id,
    )