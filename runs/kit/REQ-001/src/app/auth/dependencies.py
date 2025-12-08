"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.domain import User, UserRole
from app.auth.errors import (
    AuthenticationError,
    AuthorizationError,
    TokenExpiredError,
    TokenValidationError,
)
from app.auth.oidc import OIDCClient, TokenPayload
from app.auth.repository import UserRepository

# Security scheme for Bearer token
bearer_scheme = HTTPBearer(auto_error=False)


def get_oidc_client(request: Request) -> OIDCClient:
    """Get OIDC client from app state."""
    oidc_client = getattr(request.app.state, "oidc_client", None)
    if not oidc_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "OIDC_NOT_CONFIGURED", "message": "OIDC client not configured"},
        )
    return oidc_client


def get_user_repository(request: Request) -> UserRepository:
    """Get user repository from app state."""
    user_repo = getattr(request.app.state, "user_repository", None)
    if not user_repo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "REPO_NOT_CONFIGURED", "message": "User repository not configured"},
        )
    return user_repo


async def get_token_payload(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    oidc_client: Annotated[OIDCClient, Depends(get_oidc_client)],
) -> TokenPayload:
    """Extract and validate token from Authorization header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authorization token required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = await oidc_client.validate_access_token(credentials.credentials)
        return payload
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except TokenValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    token_payload: Annotated[TokenPayload, Depends(get_token_payload)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Get current authenticated user from token."""
    user = await user_repo.get_by_oidc_sub(token_payload.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not registered"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    oidc_client: Annotated[OIDCClient, Depends(get_oidc_client)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    try:
        payload = await oidc_client.validate_access_token(credentials.credentials)
        return await user_repo.get_by_oidc_sub(payload.sub)
    except (TokenExpiredError, TokenValidationError, AuthenticationError):
        return None


def require_role(*roles: UserRole) -> Callable[[User], User]:
    """Create dependency that requires user to have one of the specified roles."""

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Required role: {', '.join(r.value for r in roles)}",
                },
            )
        return current_user

    return role_checker


def require_any_role(*roles: UserRole) -> Callable[[User], User]:
    """Alias for require_role - requires any of the specified roles."""
    return require_role(*roles)


# Pre-configured role dependencies for common use cases
RequireAdmin = Depends(require_role(UserRole.ADMIN))
RequireWriter = Depends(require_role(UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER))
RequireReader = Depends(
    require_role(UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER, UserRole.VIEWER)
)