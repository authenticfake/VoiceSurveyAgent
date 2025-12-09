"""
Authentication and authorization utilities.

REQ-017: Campaign dashboard stats API
"""

import logging
from enum import Enum
from functools import wraps
from typing import Callable, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"


class CurrentUser(BaseModel):
    """Current authenticated user."""

    id: UUID
    email: str
    name: str
    role: UserRole
    oidc_sub: str


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """Extract and validate current user from JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        email = payload.get("email")
        name = payload.get("name", "")
        role = payload.get("role", "viewer")
        oidc_sub = payload.get("oidc_sub", user_id)

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )

        return CurrentUser(
            id=UUID(user_id),
            email=email,
            name=name,
            role=UserRole(role),
            oidc_sub=oidc_sub,
        )
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(*allowed_roles: UserRole) -> Callable:
    """Decorator to require specific roles for endpoint access."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find current_user in kwargs
            current_user: Optional[CurrentUser] = kwargs.get("current_user")
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            if current_user.role not in allowed_roles:
                logger.warning(
                    f"Access denied for user {current_user.id} "
                    f"with role {current_user.role} to endpoint requiring {allowed_roles}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator