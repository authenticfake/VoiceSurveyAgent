"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import CurrentUser
from app.auth.schemas import (
    AuthCallbackResponse,
    AuthLoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserProfile,
)
from app.auth.service import AuthService
from app.config import get_settings
from app.shared.database import get_db_session
from app.shared.exceptions import AuthenticationError, OIDCError
from app.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory state storage (should use Redis in production)
_pending_states: dict[str, bool] = {}

def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    """Dependency for auth service."""
    return AuthService(session)

@router.get("/login", response_model=AuthLoginResponse)
async def login(
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthLoginResponse:
    """Initiate OIDC login flow.

    Returns the authorization URL to redirect the user to.
    """
    response = await service.initiate_login()
    # Store state for validation
    _pending_states[response.state] = True
    return response

@router.get("/callback", response_model=AuthCallbackResponse)
async def callback(
    code: Annotated[str, Query(description="Authorization code from IdP")],
    state: Annotated[str, Query(description="State parameter for CSRF protection")],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthCallbackResponse:
    """Handle OIDC callback.

    Exchanges the authorization code for tokens and creates a user session.
    """
    # Validate state
    if state not in _pending_states:
        logger.warning("Invalid or expired state in callback")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state",
        )

    # Remove used state
    del _pending_states[state]

    try:
        return await service.handle_callback(code, state, state)
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
    except OIDCError as e:
        logger.error(f"OIDC error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication provider error",
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshTokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Refresh access token using refresh token."""
    try:
        return await service.refresh_session(request.refresh_token)
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: CurrentUser,
) -> UserProfile:
    """Get current user profile.

    Requires authentication.
    """
    return UserProfile.model_validate(current_user)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: CurrentUser,
    response: Response,
) -> None:
    """Logout current user.

    Clears the session cookie. Note: This doesn't invalidate the JWT token
    on the server side. For full logout, implement token blacklisting.
    """
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=settings.session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    logger.info(f"User logged out: {current_user.id}")