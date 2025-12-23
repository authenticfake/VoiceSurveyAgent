"""
Authentication API router.

REQ-002: OIDC authentication integration
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import CurrentUserDep
from app.auth.schemas import (
    AuthCallbackResponse,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserProfile,
)
from app.auth.service import AuthService
from app.shared.database import get_db_session
from app.shared.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    OIDCError,
    TokenExpiredError,
    UserNotFoundError,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory state storage for demo purposes
# In production, use Redis or database with TTL
_state_storage: dict[str, bool] = {}


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    """Dependency for auth service."""
    return AuthService(session=session)


@router.get("/login", response_model=LoginResponse)
async def login(
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    """Initiate OIDC login flow.

    Returns the authorization URL to redirect the user to the IdP.
    The state parameter should be stored client-side for CSRF validation.
    """
    response = service.initiate_login()

    # Store state for validation (in production, use Redis with TTL)
    _state_storage[response.state] = True

    return response


@router.get("/callback", response_model=AuthCallbackResponse)
async def callback(
    code: Annotated[str, Query(description="Authorization code from IdP")],
    state: Annotated[str, Query(description="State parameter for CSRF validation")],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthCallbackResponse:
    """Handle OIDC callback after user authentication.

    Exchanges the authorization code for tokens and creates/updates the user.
    """
    # Validate state exists (CSRF protection)
    if state not in _state_storage:
        logger.warning("Unknown state in callback", extra={"state": state[:8] + "..."})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STATE",
                "message": "Invalid or expired state parameter",
            },
        )

    # Remove state after use (one-time use)
    del _state_storage[state]

    try:
        return await service.handle_callback(
            code=code,
            state=state,
            expected_state=state,  # Already validated above
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )
    except OIDCError as e:
        logger.error("OIDC error in callback", extra={"error": e.message})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": e.code, "message": e.message},
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_tokens(
    request: RefreshTokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> RefreshTokenResponse:
    """Refresh access and refresh tokens.

    Requires a valid refresh token.
    """
    try:
        return await service.refresh_tokens(request.refresh_token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "Refresh token has expired",
            },
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: CurrentUserDep,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserProfile:
    """Get the current authenticated user's profile.

    Requires a valid access token.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Token missing user information",
            },
        )

    try:
        return await service.get_user_profile(current_user.id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        )