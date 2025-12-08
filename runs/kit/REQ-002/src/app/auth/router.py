"""
Authentication API router.

Defines REST endpoints for OIDC authentication flow.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import HttpUrl

from app.auth.middleware import CurrentUser
from app.auth.schemas import (
    AuthenticatedResponse,
    LoginResponse,
    RefreshRequest,
    UserContext,
    UserProfileResponse,
)
from app.auth.service import AuthService
from app.config import get_settings
from app.shared.database import DbSession
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["authentication"])


async def get_auth_service(db: DbSession) -> AuthService:
    """Dependency to get auth service instance."""
    service = AuthService(settings=settings, db_session=db)
    await service.initialize()
    return service


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.get(
    "/login",
    response_model=LoginResponse,
    summary="Initiate OIDC login",
    description="Generate authorization URL for OIDC login flow",
)
async def login(
    auth_service: AuthServiceDep,
    redirect_url: HttpUrl | None = Query(
        None,
        description="URL to redirect after successful login",
    ),
) -> LoginResponse:
    """Initiate OIDC authorization code flow."""
    auth_url, state = auth_service.generate_authorization_url(
        redirect_url=str(redirect_url) if redirect_url else None
    )

    logger.info("Login initiated", state=state[:8] + "...")

    return LoginResponse(
        authorization_url=auth_url,
        state=state,
    )


@router.get(
    "/callback",
    response_model=AuthenticatedResponse,
    summary="OIDC callback",
    description="Handle OIDC callback and exchange code for tokens",
)
async def callback(
    auth_service: AuthServiceDep,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
) -> AuthenticatedResponse:
    """Handle OIDC callback and complete authentication."""
    logger.info("Processing OIDC callback", state=state[:8] + "...")

    response = await auth_service.exchange_code_for_tokens(code=code, state=state)

    logger.info(
        "Authentication successful",
        user_id=str(response.user.id),
        email=response.user.email,
    )

    return response


@router.post(
    "/refresh",
    response_model=AuthenticatedResponse,
    summary="Refresh tokens",
    description="Refresh access token using refresh token",
)
async def refresh(
    auth_service: AuthServiceDep,
    request: RefreshRequest,
) -> AuthenticatedResponse:
    """Refresh access token using refresh token."""
    logger.info("Token refresh requested")

    response = await auth_service.refresh_tokens(request.refresh_token)

    logger.info(
        "Token refresh successful",
        user_id=str(response.user.id),
    )

    return response


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Get profile information for the authenticated user",
)
async def get_profile(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> UserProfileResponse:
    """Get current user profile."""
    user = await auth_service.get_user_by_id(current_user.id)

    if not user:
        from app.shared.exceptions import NotFoundError

        raise NotFoundError(
            message="User not found",
            resource_type="User",
            resource_id=str(current_user.id),
        )

    return UserProfileResponse(
        id=user.id,
        oidc_sub=user.oidc_sub,
        email=user.email,
        name=user.name,
        role=current_user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Logout current user (client should discard tokens)",
)
async def logout(
    current_user: CurrentUser,
) -> None:
    """Logout current user.

    Note: This endpoint is primarily for audit logging.
    The client is responsible for discarding tokens.
    """
    logger.info(
        "User logged out",
        user_id=str(current_user.id),
        email=current_user.email,
    )