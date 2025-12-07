from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain.models import Role
from app.auth.domain.schemas import (
    AuthTokensResponse,
    ErrorResponse,
    OidcCallbackRequest,
    OidcLoginResponse,
    UserRead,
)
from app.auth.errors import AuthError, AuthErrorCode
from app.auth.rbac import get_current_user, require_roles
from app.auth.service import AuthService, build_auth_service
from app.infra.config.settings import Settings, get_settings
from app.infra.db.session import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return build_auth_service(session, settings)


@router.get("/login", response_model=OidcLoginResponse)
async def login_redirect(
    redirect_uri: str,
    service: AuthService = Depends(get_auth_service),
) -> OidcLoginResponse:
    payload = service.build_authorization_url(redirect_uri)
    return OidcLoginResponse(**payload)


@router.post(
    "/callback",
    response_model=AuthTokensResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def oidc_callback(
    request: OidcCallbackRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return await service.complete_login(
            code=request.code,
            redirect_uri=request.redirect_uri,
        )
    except AuthError as exc:
        status_code = (
            status.HTTP_401_UNAUTHORIZED
            if exc.code in {AuthErrorCode.INVALID_TOKEN, AuthErrorCode.UNAUTHORIZED}
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=ErrorResponse(
                error=exc.code.value,
                error_description=exc.description,
            ).model_dump(),
        ) from exc


@router.get(
    "/me",
    response_model=UserRead,
    dependencies=[Depends(require_roles(Role.VIEWER, Role.CAMPAIGN_MANAGER, Role.ADMIN))],
)
async def get_me(current_user=Depends(get_current_user)):
    return UserRead.from_domain(current_user)


@router.get(
    "/manager/ping",
    dependencies=[Depends(require_roles(Role.CAMPAIGN_MANAGER, Role.ADMIN))],
)
async def manager_ping():
    return {"status": "ok"}


@router.get(
    "/admin/ping",
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
async def admin_ping():
    return {"status": "ok"}