from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class Role(str, Enum):
    viewer = "viewer"
    campaign_manager = "campaign_manager"
    admin = "admin"


@dataclass(slots=True)
class User:
    id: UUID
    oidc_sub: str
    email: str
    name: str
    role: Role
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class OIDCProfile:
    sub: str
    email: str
    name: str | None = None
    roles: list[str] | None = None


@dataclass(slots=True)
class TokenSet:
    access_token: str
    id_token: str
    expires_in: int
    refresh_token: str | None = None
    token_type: str = "Bearer"


@dataclass(slots=True)
class IDTokenClaims:
    subject: str
    email: str | None
    name: str | None
    issuer: str
    audience: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    raw_claims: dict[str, Any]