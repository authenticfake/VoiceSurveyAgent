from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_current_user, get_oidc_client, get_token_service
from app.auth.schemas import (
    CallbackRequest,
    LoginRedirectResponse,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
)
from app.auth.service import AuthService
from app.config import get_settings
from app.shared.models.user import User


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/login", response_model=LoginRedirectResponse)
async def login_redirect(
    redirect_uri: str | None = None,
    auth_service: AuthService = Depends(),
):
    return auth_service.build_authorization_url(redirect_uri)


@router.post("/callback", response_model=LoginResponse)
async def auth_callback(
    request: Request,
    payload: CallbackRequest,
    auth_service: AuthService = Depends(),
):
    client_ip = request.client.host if request.client else "0.0.0.0"
    agent = request.headers.get("User-Agent", "unknown")
    return await auth_service.handle_callback(payload, client_ip, agent)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_tokens(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(),
):
    return auth_service.refresh_session(payload)


@router.get("/me", response_model=LoginResponse["user"])  # type: ignore[index]
async def current_user(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }