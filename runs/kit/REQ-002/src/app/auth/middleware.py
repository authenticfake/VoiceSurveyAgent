"""
Authentication middleware for JWT validation.

REQ-002: OIDC authentication integration
REQ-003: RBAC authorization middleware - Extended with role extraction

This module exposes:
- TokenValidatorProtocol
- JWTTokenValidator
- CurrentUser
- get_current_user
- CurrentUserDep (FastAPI dependency, wrapper-based for test patching)
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import Annotated, Protocol
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.shared.database import get_db_session
from app.shared.exceptions import InvalidTokenError, TokenExpiredError
from app.shared.logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Current authenticated user information."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(..., description="User ID")
    oidc_sub: str = Field(..., description="OIDC subject identifier")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    role: str = Field(..., description="User role")


class TokenValidatorProtocol(Protocol):
    """Protocol for token validation."""

    def validate_access_token(self, token: str) -> dict: ...


class JWTTokenValidator:
    """JWT token validator."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def validate_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
            )

            if payload.get("type") != "access":
                raise InvalidTokenError(
                    message="Invalid token type",
                    details={"expected": "access", "got": payload.get("type")},
                )

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
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """Extract and validate current user from JWT token.

    Role is extracted from JWT claims or fetched from DB (fallback).
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

        user_id = payload.get("user_id")
        if user_id is None:
            raise InvalidTokenError(
                message="Token missing user_id",
                details={"payload_keys": list(payload.keys())},
            )

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
            oidc_sub=payload.get("sub", "") or "",
            email=payload.get("email", "") or "",
            name=payload.get("name", "") or "",
            role=role,
        )

    except TokenExpiredError:
        logger.info(
            "Token expired",
            extra={"endpoint": str(request.url.path), "method": request.method},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Token has expired"},
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
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def _get_current_user_dep(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """
    Wrapper dependency that resolves get_current_user at runtime.

    This makes unit tests that patch `app.auth.middleware.get_current_user`
    work reliably: FastAPI depends on this wrapper, and the wrapper picks up
    the patched function.
    """
    result = get_current_user(
        request=request,
        credentials=credentials,
        session=session,
        settings=settings,
    )
    if inspect.isawaitable(result):
        return await result
    return result  # type: ignore[return-value]


# Dependency aliases
CurrentUserDep = Annotated[CurrentUser, Depends(_get_current_user_dep)]
AuthenticatedUser = CurrentUser
AuthenticatedUserDep = CurrentUserDep


