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
        description="Optional redirect URL override",
    ),
) -> LoginResponse:
    """Generate OIDC authorization URL."""
    url, state = auth_service.generate_authorization_url(
        redirect_url=str(redirect_url) if redirect_url else None
    )
    return LoginResponse(authorization_url=HttpUrl(url), state=state)


@router.get(
    "/callback",
    response_model=AuthenticatedResponse,
    summary="OIDC callback",
    description="Handle OIDC provider callback and exchange code for tokens",
)
async def callback(
    auth_service: AuthServiceDep,
    code: str = Query(..., description="Authorization code from OIDC provider"),
    state: str = Query(..., description="CSRF state parameter"),
    redirect_url: HttpUrl | None = Query(
        None,
        description="Optional redirect URL override",
    ),
) -> AuthenticatedResponse:
    """Handle OIDC callback and complete authentication."""
    return await auth_service.authenticate(
        code=code,
        state=state,
        redirect_url=str(redirect_url) if redirect_url else None,
    )


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
    """Refresh access token."""
    return await auth_service.refresh_tokens(request.refresh_token)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user",
    description="Get profile of currently authenticated user",
)
async def get_me(
    current_user: CurrentUser,
    db: DbSession,
) -> UserProfileResponse:
    """Get current user profile."""
    from app.auth.service import AuthService

    auth_service = AuthService(settings=settings, db_session=db)
    user = await auth_service.get_user_by_id(current_user.id)

    if not user:
        # This shouldn't happen if middleware worked correctly
        raise ValueError("User not found")

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=current_user.role,
        created_at=user.created_at,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Logout current user (client should discard tokens)",
)
async def logout(current_user: CurrentUser) -> None:
    """
    Logout endpoint.

    Note: With JWT tokens, actual logout is handled client-side
    by discarding the tokens. This endpoint is provided for
    API completeness and logging purposes.
    """
    logger.info(
        "User logged out",
        extra={"user_id": str(current_user.id)},
    )