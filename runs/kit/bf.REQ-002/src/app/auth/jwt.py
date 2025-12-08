"""JWT token handling for session management."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.config import Settings, get_settings
from app.shared.exceptions import TokenExpiredError, TokenInvalidError
from app.shared.logging import get_logger

logger = get_logger(__name__)

class JWTHandler:
    """Handler for creating and validating JWT tokens."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        role: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create a new access token."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self._settings.jwt_access_token_expire_minutes)

        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": expires,
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm="HS256",
        )

    def create_refresh_token(
        self,
        user_id: UUID,
    ) -> str:
        """Create a new refresh token."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=self._settings.jwt_refresh_token_expire_days)

        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": now,
            "exp": expires,
        }

        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm="HS256",
        )

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=["HS256"],
            )
            return payload
        except ExpiredSignatureError as e:
            logger.warning("Token expired")
            raise TokenExpiredError() from e
        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise TokenInvalidError() from e

    def validate_access_token(self, token: str) -> dict[str, Any]:
        """Validate an access token and return its payload."""
        payload = self.decode_token(token)

        if payload.get("type") != "access":
            raise TokenInvalidError("Not an access token")

        return payload

    def validate_refresh_token(self, token: str) -> dict[str, Any]:
        """Validate a refresh token and return its payload."""
        payload = self.decode_token(token)

        if payload.get("type") != "refresh":
            raise TokenInvalidError("Not a refresh token")

        return payload

    def get_token_expiry(self) -> int:
        """Get access token expiry in seconds."""
        return self._settings.jwt_access_token_expire_minutes * 60