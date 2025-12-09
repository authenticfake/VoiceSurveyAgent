"""
Authentication and authorization utilities.

REQ-018: Campaign CSV export
"""

import logging
from datetime import datetime, timedelta
from typing import Annotated, Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.config import get_settings
from app.shared.database import get_db_session
from app.shared.models import User, UserRole

logger = logging.getLogger(__name__)
settings = get_settings()

security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str
    email: str
    name: str
    role: UserRole
    exp: datetime
    iat: datetime


class CurrentUser(BaseModel):
    """Current authenticated user."""

    id: UUID
    oidc_sub: str
    email: str
    name: str
    role: UserRole


def create_access_token(user: User) -> str:
    """Create JWT access token for user."""
    now = datetime.utcnow()
    payload = {
        "sub": user.oidc_sub,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "exp": now + timedelta(minutes=settings.jwt_expiration_minutes),
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(
            sub=payload["sub"],
            email=payload["email"],
            name=payload["name"],
            role=UserRole(payload["role"]),
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


async def get_current_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUser:
    """Get current authenticated user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )

    token_payload = decode_token(credentials.credentials)

    # Get user from database
    result = await db.execute(
        select(User).where(User.oidc_sub == token_payload.sub)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return CurrentUser(
        id=user.id,
        oidc_sub=user.oidc_sub,
        email=user.email,
        name=user.name,
        role=user.role,
    )


def require_role(*allowed_roles: UserRole):
    """Dependency factory for role-based access control."""

    async def role_checker(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role not in allowed_roles:
            logger.warning(
                "Access denied",
                extra={
                    "user_id": str(current_user.id),
                    "user_role": current_user.role.value,
                    "required_roles": [r.value for r in allowed_roles],
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(r.value for r in allowed_roles)}",
            )
        return current_user

    return role_checker


# Pre-configured role dependencies
require_admin = require_role(UserRole.ADMIN)
require_campaign_manager = require_role(UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER)
require_viewer = require_role(UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER, UserRole.VIEWER)