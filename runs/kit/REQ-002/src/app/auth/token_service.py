from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.auth.schemas import SessionClaims
from app.shared.models.user import User


class TokenService:
    def __init__(
        self,
        secret_key: str,
        issuer: str,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
    ):
        self.secret_key = secret_key
        self.issuer = issuer
        self.access_ttl = timedelta(seconds=access_ttl_seconds)
        self.refresh_ttl = timedelta(seconds=refresh_ttl_seconds)
        self.algorithm = "HS256"

    def _build_payload(self, user: User, token_type: str, ttl: timedelta) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "iss": self.issuer,
            "sub": str(user.id),
            "role": user.role,
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int((now + ttl).timestamp()),
            "jti": str(uuid.uuid4()),
        }

    def create_session_tokens(self, user: User) -> Tuple[str, str, int]:
        access_payload = self._build_payload(user, "access", self.access_ttl)
        refresh_payload = self._build_payload(user, "refresh", self.refresh_ttl)
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(
            refresh_payload, self.secret_key, algorithm=self.algorithm
        )
        expires_in = int(self.access_ttl.total_seconds())
        return access_token, refresh_token, expires_in

    def _decode(self, token: str) -> SessionClaims:
        try:
            data = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["exp", "iat", "jti", "type"]},
            )
        except ExpiredSignatureError as exc:
            raise InvalidTokenError("token_expired") from exc
        except InvalidTokenError as exc:  # pragma: no cover - same raise
            raise InvalidTokenError("token_invalid") from exc
        return SessionClaims(**data)

    def validate_access_token(self, token: str) -> SessionClaims:
        claims = self._decode(token)
        if claims.type != "access":  # pragma: no cover - double guard
            raise InvalidTokenError("invalid_token_type")
        return claims

    def validate_refresh_token(self, token: str) -> SessionClaims:
        claims = self._decode(token)
        if claims.type != "refresh":
            raise InvalidTokenError("invalid_refresh_token")
        return claims