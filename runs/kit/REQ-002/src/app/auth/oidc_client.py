from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import httpx
from pydantic import BaseModel, EmailStr

from app.config import OIDCSettings


class OIDCError(RuntimeError):
    pass


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    id_token: str | None
    expires_in: int


class UserInfo(BaseModel):
    sub: str
    email: EmailStr
    name: str
    role: str | None = None


class OIDCClient:
    def __init__(
        self,
        settings: OIDCSettings,
        http_client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    ):
        self.settings = settings
        self.http_client_factory = http_client_factory or (
            lambda: httpx.AsyncClient(timeout=10)
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenSet:
        async with self.http_client_factory() as client:
            response = await client.post(
                str(self.settings.token_endpoint),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.settings.client_id,
                    "client_secret": self.settings.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code >= 400:
                raise OIDCError("token_exchange_failed")
            payload = response.json()
            return TokenSet(
                access_token=payload["access_token"],
                refresh_token=payload.get("refresh_token", ""),
                id_token=payload.get("id_token"),
                expires_in=payload.get("expires_in", 3600),
            )

    async def fetch_userinfo(self, access_token: str) -> UserInfo:
        async with self.http_client_factory() as client:
            response = await client.get(
                str(self.settings.userinfo_endpoint),
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code >= 400:
                raise OIDCError("userinfo_failed")
            return UserInfo(**response.json())