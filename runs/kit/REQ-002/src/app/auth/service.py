from __future__ import annotations

from urllib.parse import urlencode

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.oidc_client import OIDCClient, OIDCError
from app.auth.repository import UserRepository
from app.auth.schemas import (
    CallbackRequest,
    LoginRedirectResponse,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
)
from app.auth.token_service import TokenService
from app.config import AppSettings, get_settings
from app.shared.database import get_session


class AuthService:
    def __init__(
        self,
        settings: AppSettings = Depends(get_settings),
        token_service: TokenService = Depends(lambda: None),
        oidc_client: OIDCClient = Depends(lambda: None),
        session: Session = Depends(get_session),
    ):
        if token_service is None or oidc_client is None:
            raise RuntimeError("Dependencies must be provided")
        self.settings = settings
        self.token_service = token_service
        self.oidc_client = oidc_client
        self.session = session
        self.user_repo = UserRepository(session)

    def build_authorization_url(self, redirect_uri: str | None) -> LoginRedirectResponse:
        target_redirect = redirect_uri or str(self.settings.oidc.default_redirect_uri)
        params = urlencode(
            {
                "client_id": self.settings.oidc.client_id,
                "redirect_uri": target_redirect,
                "response_type": "code",
                "scope": self.settings.oidc.scope,
                "state": TokenService._build_state(),  # type: ignore[attr-defined]
            }
        )
        return LoginRedirectResponse(
            authorization_url=f"{self.settings.oidc.authorization_endpoint}?{params}",
            state=params.split("state=")[-1],
        )

    async def handle_callback(self, data: CallbackRequest, ip: str, agent: str) -> LoginResponse:
        redirect_uri = str(
            data.redirect_uri or self.settings.oidc.default_redirect_uri
        )
        try:
            provider_tokens = await self.oidc_client.exchange_code(
                data.code, redirect_uri
            )
            userinfo = await self.oidc_client.fetch_userinfo(provider_tokens.access_token)
        except OIDCError:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="oidc_error")
        user = self.user_repo.upsert_oidc_user(
            sub=userinfo.sub,
            email=userinfo.email,
            name=userinfo.name,
            role=userinfo.role,
            last_login_ip=ip,
            user_agent=agent,
        )
        access_token, refresh_token, expires_in = self.token_service.create_session_tokens(
            user
        )
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
            },
        )

    def refresh_session(self, data: RefreshRequest) -> RefreshResponse:
        try:
            claims = self.token_service.validate_refresh_token(data.refresh_token)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")
        user = self.user_repo.get_by_id(claims.sub)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
        access_token, refresh_token, expires_in = self.token_service.create_session_tokens(
            user
        )
        return RefreshResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )