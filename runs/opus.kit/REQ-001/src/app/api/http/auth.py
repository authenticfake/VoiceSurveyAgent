"""Authentication API routes."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user, get_oidc_client, get_user_repository
from app.auth.domain import User, UserResponse, UserRole
from app.auth.errors import AuthenticationError, OIDCConfigurationError
from app.auth.oidc import OIDCClient
from app.auth.repository import UserRepository
from app.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginResponse(BaseModel):
    """Login initiation response."""

    authorization_url: str = Field(..., description="URL to redirect user for login")
    state: str = Field(..., description="State parameter for CSRF protection")


class CallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="State parameter")


class TokensResponse(BaseModel):
    """Token response after successful authentication."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    id_token: Optional[str] = None
    user: UserResponse


class ErrorResponse(BaseModel):
    """Standard error response."""

    code: str
    message: str


@router.get("/login", response_model=LoginResponse)
async def initiate_login(
    request: Request,
    oidc_client: Annotated[OIDCClient, Depends(get_oidc_client)],
) -> LoginResponse:
    """
    Initiate OIDC login flow.

    Returns authorization URL and state for client to redirect user.
    """
    user_repo = getattr(request.app.state, "user_repository", None)
    if not user_repo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "REPO_NOT_CONFIGURED", "message": "User repository not configured"},
        )

    auth_service = AuthService(oidc_client, user_repo)
    state = auth_service.generate_state()

    try:
        auth_url = auth_service.get_login_url(state)
    except OIDCConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": e.code, "message": e.message},
        ) from e

    return LoginResponse(authorization_url=auth_url, state=state)


@router.post("/callback", response_model=TokensResponse)
async def handle_callback(
    request: Request,
    callback_data: CallbackRequest,
    oidc_client: Annotated[OIDCClient, Depends(get_oidc_client)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> TokensResponse:
    """
    Handle OAuth callback after user authentication.

    Exchanges authorization code for tokens and creates/updates user.
    """
    auth_service = AuthService(oidc_client, user_repo)

    try:
        user, tokens = await auth_service.handle_callback(callback_data.code)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        ) from e
    except OIDCConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": e.code, "message": e.message},
        ) from e

    return TokensResponse(
        access_token=tokens.access_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        id_token=tokens.id_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/callback")
async def handle_callback_get(
    request: Request,
    code: Annotated[str, Query(description="Authorization code")],
    state: Annotated[str, Query(description="State parameter")],
    oidc_client: Annotated[OIDCClient, Depends(get_oidc_client)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> TokensResponse:
    """
    Handle OAuth callback via GET (browser redirect).

    Exchanges authorization code for tokens and creates/updates user.
    """
    auth_service = AuthService(oidc_client, user_repo)

    try:
        user, tokens = await auth_service.handle_callback(code)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        ) from e
    except OIDCConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": e.code, "message": e.message},
        ) from e

    return TokensResponse(
        access_token=tokens.access_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        id_token=tokens.id_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """
    Logout current user.

    Note: This endpoint only acknowledges logout on the application side.
    Full OIDC logout may require redirect to provider's end_session_endpoint.
    """
    # In a real implementation, you might invalidate server-side sessions here
    return {"message": "Logged out successfully"}