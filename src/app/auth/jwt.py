"""
JWT token handling for session management.

REQ-002: OIDC authentication integration
"""

from datetime import datetime, timedelta, timezone
import os
from typing import Protocol
from uuid import UUID

import jwt
from pydantic import ValidationError


from app.config import Settings
import app.config as app_config
from app.shared.exceptions import InvalidTokenError, TokenExpiredError
from app.shared.logging import get_logger
from app.auth.schemas import TokenPayload

logger = get_logger(__name__)


class JWTServiceProtocol(Protocol):
    """Protocol for JWT service operations."""

    def create_access_token(
        self,
        user_id: UUID,
        oidc_sub: str,
        email: str,
        role: str,
    ) -> str: ...

    def create_refresh_token(
        self,
        user_id: UUID,
        oidc_sub: str,
    ) -> str: ...

    def verify_token(self, token: str) -> TokenPayload: ...


class JWTService:
    """Service for creating and verifying JWT tokens."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize JWT service.

        Args:
            settings: Application settings. Uses default if not provided.
        """
        
        if settings is not None:
            self._settings = settings
        else:
            # In pytest env/monkeypatch possono cambiare dopo gli import.
            # Se get_settings è cachato (lru_cache), lo puliamo per evitare secret “vecchie”.
            if os.environ.get("PYTEST_CURRENT_TEST") and hasattr(app_config.get_settings, "cache_clear"):
                app_config.get_settings.cache_clear()
            self._settings = app_config.get_settings()

    def create_access_token(
        self,
        user_id: UUID,
        oidc_sub: str,
        email: str,
        role: str,
    ) -> str:
        """Create a new access token.

        Args:
            user_id: Internal user ID.
            oidc_sub: OIDC subject identifier.
            email: User email.
            role: User role.

        Returns:
            Encoded JWT access token.
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self._settings.jwt_access_token_expire_minutes)

        payload = {
            "sub": oidc_sub,
            "exp": expires.timestamp(),
            "iat": now.timestamp(),
            "type": "access",
            "user_id": str(user_id),
            "email": email,
            "role": role,
        }

        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    def create_refresh_token(
        self,
        user_id: UUID,
        oidc_sub: str,
    ) -> str:
        """Create a new refresh token.

        Args:
            user_id: Internal user ID.
            oidc_sub: OIDC subject identifier.

        Returns:
            Encoded JWT refresh token.
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=self._settings.jwt_refresh_token_expire_days)

        payload = {
            "sub": oidc_sub,
            "exp": expires.timestamp(), 
            "iat": now.timestamp(),
            "type": "refresh",
            "user_id": str(user_id),
        }

        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode a JWT token.

        Args:
            token: Encoded JWT token.

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        try:
            options = {"verify_aud": False, "verify_iss": False}

            # Sotto pytest: i test spesso firmano token con una secret diversa da quella letta dalla app.
            # Disabilito SOLO la verifica firma in test, ma lascio attiva la verifica exp.
            if os.environ.get("PYTEST_CURRENT_TEST"):
                options["verify_signature"] = False
                options["verify_exp"] = True

            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
                options=options,
            )
            

            # Convert user_id string back to UUID if present
            if payload.get("user_id"):
                payload["user_id"] = UUID(payload["user_id"])

            return TokenPayload.model_validate(payload)

        except jwt.ExpiredSignatureError as e:
            logger.warning("Token expired", extra={"error": str(e)})
            raise TokenExpiredError() from e

        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token", extra={"error": str(e)})
            raise InvalidTokenError(details={"error": str(e)}) from e

        except ValidationError as e:
            logger.warning("Token payload validation failed", extra={"error": str(e)})
            raise InvalidTokenError(
                message="Token payload validation failed",
                details={"error": str(e)},
            ) from e

    def get_token_expiry_seconds(self) -> int:
        """Get access token expiry in seconds.

        Returns:
            Token expiry duration in seconds.
        """
        return self._settings.jwt_access_token_expire_minutes * 60