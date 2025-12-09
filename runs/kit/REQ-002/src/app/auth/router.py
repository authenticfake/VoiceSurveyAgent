"""Authentication API routes."""
import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config import AuthConfig
from app.auth.dependencies import get_auth_config, get_auth_service, get_current_user
from app.auth.exceptions import AuthenticationError, InvalidStateError, OIDCProviderError
from app.auth.models import (
    AuthErrorResponse,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.auth.service import AuthService
from app.shared.database import get_db
from app.shared.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory state storage (use Redis in production)
_state_storage: dict[str, str] = {}

@router.get(
    "/login",
    summary="Initiate OIDC login",
    description="Redirects to OIDC provider for authentication"
)
async def login(
    request: Request,
    redirect_uri: Optional[str] = Query(
        None,
        description="Custom redirect URI after login"
    ),
    config: AuthConfig = Depends(get_auth_config),
    auth_service: AuthService = Depends(get_auth_service)
) -> RedirectResponse:
    """Initiate OIDC authorization code flow.
    
    Args:
        request: FastAPI request
        redirect_uri: Optional custom redirect URI
        config: Auth configuration
        auth_service: Authentication service
        
    Returns:
        Redirect to OIDC provider
    """
    if not config.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC not configured"
        )
    
    # Generate and store state
    state = auth_service.generate_state()
    _state_storage[state] = redirect_uri or config.redirect_uri
    
    # Get authorization URL
    auth_url = auth_service.get_authorization_url(state, redirect_uri)
    
    logger.info("Initiating OIDC login, redirecting to provider")
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)

@router.get(
    "/callback",
    summary="OIDC callback",
    description="Handles OIDC provider callback after authentication",
    response_model=LoginResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Invalid callback"},
        502: {"model": AuthErrorResponse, "description": "OIDC provider error"}
    }
)
async def callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="CSRF state parameter"),
    error: Optional[str] = Query(None, description="Error code from provider"),
    error_description: Optional[str] = Query(
        None,
        description="Error description"
    ),
    db: AsyncSession = Depends(get_db),
    config: AuthConfig = Depends(get_auth_config),
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    """Handle OIDC callback and complete authentication.
    
    Args:
        code: Authorization code from provider
        state: CSRF state parameter
        error: Optional error code
        error_description: Optional error description
        db: Database session
        config: Auth configuration
        auth_service: Authentication service
        
    Returns:
        Login response with tokens and user profile
    """
    # Check for error from provider
    if error:
        logger.warning("OIDC provider returned error: %s - %s", error, error_description)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_description or error
        )
    
    # Validate state
    stored_redirect = _state_storage.pop(state, None)
    if stored_redirect is None:
        logger.warning("Invalid or expired state parameter")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    
    try:
        # Exchange code and get/create user
        user, access_token, refresh_token = await auth_service.exchange_code_and_get_user(
            code,
            db,
            stored_redirect
        )
        
        logger.info(
            "User authenticated successfully: %s (%s)",
            user.email,
            user.oidc_sub
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=config.access_token_expire_minutes * 60,
            refresh_token=refresh_token,
            user=UserProfileResponse.model_validate(user)
        )
        
    except OIDCProviderError as e:
        logger.error("OIDC provider error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )

@router.post(
    "/refresh",
    summary="Refresh access token",
    description="Exchange refresh token for new access token",
    response_model=TokenResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Invalid refresh token"},
        502: {"model": AuthErrorResponse, "description": "OIDC provider error"}
    }
)
async def refresh(
    request: RefreshTokenRequest,
    config: AuthConfig = Depends(get_auth_config),
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """Refresh access token using refresh token.
    
    Args:
        request: Refresh token request
        config: Auth configuration
        auth_service: Authentication service
        
    Returns:
        New token response
    """
    try:
        access_token, new_refresh_token = await auth_service.refresh_tokens(
            request.refresh_token
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=config.access_token_expire_minutes * 60,
            refresh_token=new_refresh_token
        )
        
    except OIDCProviderError as e:
        logger.error("Token refresh failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired refresh token"
        )

@router.get(
    "/me",
    summary="Get current user profile",
    description="Returns the authenticated user's profile",
    response_model=UserProfileResponse,
    responses={
        401: {"model": AuthErrorResponse, "description": "Not authenticated"}
    }
)
async def get_me(
    current_user: User = Depends(get_current_user)
) -> UserProfileResponse:
    """Get current authenticated user's profile.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile
    """
    return UserProfileResponse.model_validate(current_user)

@router.post(
    "/logout",
    summary="Logout user",
    description="Invalidates the current session",
    status_code=status.HTTP_204_NO_CONTENT
)
async def logout(
    current_user: User = Depends(get_current_user)
) -> Response:
    """Logout current user.
    
    Note: With JWT tokens, true logout requires token blacklisting
    or short token expiration. This endpoint is a placeholder for
    client-side token removal.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Empty response
    """
    logger.info("User logged out: %s", current_user.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)