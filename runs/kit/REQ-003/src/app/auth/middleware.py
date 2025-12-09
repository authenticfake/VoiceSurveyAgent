"""
Authentication middleware for JWT validation.

REQ-002: OIDC authentication integration
REQ-003: RBAC authorization middleware - Extended with role extraction
"""

from datetime import datetime, timezone
from typing import Annotated, Protocol
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.shared.database import get_db_session
from app.shared.exceptions import InvalidTokenError, TokenExpiredError
from app.shared.logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Current authenticated user information."""

    id: UUID = Field(..., description="User ID")
    oidc_sub: str = Field(..., description="OIDC subject identifier")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    role: str = Field(..., description="User role")

    class Config:
        """Pydantic configuration."""

        frozen = True


class TokenValidatorProtocol(Protocol):
    """Protocol for token validation."""

    def validate_access_token(self, token: str) -> dict: ...


class JWTTokenValidator:
    """JWT token validator."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize token validator.

        Args:
            settings: Application settings.
        """
        self._settings = settings or get_settings()

    def validate_access_token(self, token: str) -> dict:
        """Validate an access token and return its payload.

        Args:
            token: JWT access token.

        Returns:
            Token payload dictionary.

        Raises:
            TokenExpiredError: If token has expired.
            InvalidTokenError: If token is invalid.
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
            )

            # Check token type
            if payload.get("type") != "access":
                raise InvalidTokenError(
                    message="Invalid token type",
                    details={"expected": "access", "got": payload.get("type")},
                )

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(
                timezone.utc
            ):
                raise TokenExpiredError()

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(
                message="Invalid token",
                details={"error": str(e)},
            )


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """Extract and validate current user from JWT token.

    This dependency validates the JWT token and extracts user information.
    Role is extracted from JWT claims or fetched from database.

    Args:
        request: FastAPI request object.
        credentials: HTTP Bearer credentials.
        session: Database session.
        settings: Application settings.

    Returns:
        CurrentUser with validated user information.

    Raises:
        HTTPException: If authentication fails.
    """
    if credentials is None:
        logger.warning(
            "Missing authentication credentials",
            extra={
                "endpoint": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "MISSING_CREDENTIALS",
                "message": "Authentication credentials required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        validator = JWTTokenValidator(settings)
        payload = validator.validate_access_token(credentials.credentials)

        # Extract user information from token
        user_id = payload.get("user_id")
        if user_id is None:
            raise InvalidTokenError(
                message="Token missing user_id",
                details={"payload_keys": list(payload.keys())},
            )

        # Role can come from JWT claims or we could fetch from DB
        # For performance, we prefer JWT claims
        role = payload.get("role")
        if role is None:
            # Fallback: fetch from database if not in token
            from app.auth.repository import UserRepository

            repo = UserRepository(session)
            user = await repo.get_by_id(UUID(user_id))
            if user is None:
                raise InvalidTokenError(
                    message="User not found",
                    details={"user_id": user_id},
                )
            role = user.role

        return CurrentUser(
            id=UUID(user_id),
            oidc_sub=payload.get("sub", ""),
            email=payload.get("email", ""),
            name=payload.get("name", ""),
            role=role,
        )

    except TokenExpiredError:
        logger.info(
            "Token expired",
            extra={
                "endpoint": str(request.url.path),
                "method": request.method,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "Token has expired",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        logger.warning(
            "Invalid token",
            extra={
                "endpoint": str(request.url.path),
                "method": request.method,
                "error": e.message,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": e.code,
                "message": e.message,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


# Type alias for dependency injection
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]