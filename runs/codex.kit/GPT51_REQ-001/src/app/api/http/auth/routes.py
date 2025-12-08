from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.http.auth.dependencies import CurrentUser
from app.auth.oidc import OIDCAuthenticator, OIDCError
from app.infra.config import get_settings
from app.api.http.auth.dependencies import get_oidc_authenticator

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginUrlResponse(BaseModel):
    authorization_url: str
    state: str


class LoginCallbackResponse(BaseModel):
    token: str
    user: Dict[str, Any]


@router.get("/login-url", response_model=LoginUrlResponse)
async def get_login_url(
    state: str = Query(..., description="Opaque state for CSRF protection"),
    authenticator: OIDCAuthenticator = Depends(get_oidc_authenticator),
) -> LoginUrlResponse:
    """Return the IdP authorization URL for initiating the OIDC login flow."""
    url = authenticator.build_authorization_url(state=state)
    return LoginUrlResponse(authorization_url=url, state=state)


@router.get("/callback", response_model=LoginCallbackResponse)
async def oidc_callback(
    code: str = Query(..., description="Authorization code from IdP"),
    state: str = Query(..., description="Opaque state from original request"),
    authenticator: OIDCAuthenticator = Depends(get_oidc_authenticator),
) -> LoginCallbackResponse:
    """OIDC authorization code callback.

    Exchanges the authorization code for tokens, validates the ID token,
    upserts the user, and returns basic user info plus the ID token to
    be used as a bearer token for subsequent API requests.
    """
    # NOTE: In a full implementation, validate `state` against a signed or
    # persisted nonce. For slice‑1 we simply echo it back and do not store it.
    try:
        user, id_token = await authenticator.authenticate_via_code(code)
    except OIDCError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "oidc_error", "message": str(exc)},
        ) from exc

    return LoginCallbackResponse(
        token=id_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "state": state,
        },
    )


@router.get("/me")
async def get_me(current_user: CurrentUser):
    """Return the current authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value,
    }