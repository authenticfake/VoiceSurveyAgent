from __future__ import annotations

from typing import Annotated, Callable, Coroutine, Optional
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain.models import Role, UserProfile
from app.auth.domain.repository import SqlAlchemyUserRepository
from app.auth.domain.schemas import ErrorResponse
from app.auth.errors import AuthErrorCode
from app.infra.config.settings import Settings, get_settings
from app.infra.db.session import get_session


async def _decode_app_token(token: str, settings: Settings) -> dict:
    return jwt.decode(
        token,
        settings.app_jwt_secret.get_secret_value(),
        algorithms=[settings.app_jwt_algorithm],
        audience=settings.oidc_client_id,
        issuer=settings.app_name,
    )


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UserProfile:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error=AuthErrorCode.UNAUTHORIZED.value,
                error_description="Missing bearer token",
            ).model_dump(),
        )
    token = authorization.split(" ", 1)[1]
    try:
        payload = await _decode_app_token(token, settings)
    except jwt.PyJWTError as exc:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error=AuthErrorCode.INVALID_TOKEN.value,
                error_description=str(exc),
            ).model_dump(),
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error=AuthErrorCode.INVALID_TOKEN.value,
                error_description="Token missing subject",
            ).model_dump(),
        )

    repository = SqlAlchemyUserRepository(session)
    user = await repository.get_by_id(UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error=AuthErrorCode.UNAUTHORIZED.value,
                error_description="User not found",
            ).model_dump(),
        )
    return user


def require_roles(*allowed_roles: Role) -> Callable[[UserProfile], UserProfile]:
    """Dependency factory enforcing RBAC membership."""

    async def _dependency(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if allowed_roles and user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error=AuthErrorCode.FORBIDDEN.value,
                    error_description="Insufficient role",
                ).model_dump(),
            )
        return user

    return _dependency