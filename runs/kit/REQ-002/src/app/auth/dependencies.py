from __future__ import annotations

import secrets
import uuid

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.oidc_client import OIDCClient
from app.auth.repository import UserRepository
from app.auth.token_service import TokenService
from app.config import AppSettings, get_settings
from app.shared.database import get_session
from app.shared.models.user import User


security = HTTPBearer(auto_error=False)


def get_token_service(settings: AppSettings = Depends(get_settings)) -> TokenService:
    service = TokenService(
        secret_key=settings.tokens.secret_key,
        issuer=settings.tokens.issuer,
        access_token_ttl_seconds=settings.tokens.access_token_ttl_seconds,
        refresh_token_ttl_seconds=settings.tokens.refresh_token_ttl_seconds,
    )

    def _build_state():
        return secrets.token_urlsafe(16)

    TokenService._build_state = staticmethod(_build_state)  # type: ignore[attr-defined]
    return service


def get_oidc_client(
    settings: AppSettings = Depends(get_settings),
) -> OIDCClient:
    return OIDCClient(
        settings=settings.oidc,
        http_client_factory=lambda: httpx.AsyncClient(
            timeout=settings.http_timeout_seconds
        ),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_service: TokenService = Depends(get_token_service),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_credentials")
    try:
        claims = token_service.validate_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    repo = UserRepository(session)
    user = repo.get_by_id(uuid.UUID(str(claims.sub)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    return user