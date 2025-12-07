from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.auth.domain import UserRole, User, UserRepository
from app.auth.oidc import OIDCAuthenticator, IDTokenValidationError
from app.infra.config import get_settings


class AuthenticatedUser(BaseModel):
    """User model exposed to API route handlers via dependencies."""

    id: str
    email: str
    name: str
    role: UserRole


def get_user_repository() -> UserRepository:
    """Return the user repository.

    For slice‑1 this is left abstract. A real implementation should be
    registered via FastAPI dependency overrides in the main application.

    This function raises by default to avoid accidentally using a no-op
    implementation in production.
    """
    raise RuntimeError(
        "UserRepository dependency not configured. "
        "Provide an implementation and override get_user_repository()."
    )


def get_oidc_authenticator(
    user_repo: UserRepository = Depends(get_user_repository),
) -> OIDCAuthenticator:
    """Construct an OIDCAuthenticator with the configured UserRepository."""
    # The authenticator uses app.infra.config internally for OIDC settings.
    _ = get_settings()  # ensure settings are loadable; may raise early
    return OIDCAuthenticator(user_repository=user_repo)


async def get_current_user(
    request: Request,
    authenticator: OIDCAuthenticator = Depends(get_oidc_authenticator),
) -> AuthenticatedUser:
    """Authenticate API requests using Authorization: Bearer <id_token>.

    - Validates the ID token via OIDC.
    - Upserts or fetches the associated user record.
    - Exposes a stable AuthenticatedUser object to route handlers.
    """
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "not_authenticated", "message": "Missing bearer token"},
        )

    token = auth_header.split(" ", 1)[1].strip()
    try:
        claims = await authenticator.validate_bearer_token(token)
    except IDTokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": str(exc)},
        ) from exc

    # Upsert user based on claims
    try:
        user = authenticator._upsert_user_from_claims(claims)  # type: ignore[attr-defined]
    except IDTokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": str(exc)},
        ) from exc

    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
    )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole):
    """Factory for a dependency that enforces RBAC on route handlers."""

    async def _dependency(user: CurrentUser) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": "Operation not permitted for this role",
                    "required_roles": [r.value for r in allowed_roles],
                },
            )
        return user

    return _dependency


AdminUser = Annotated[AuthenticatedUser, Depends(require_roles(UserRole.ADMIN))]
ManagerOrAdminUser = Annotated[
    AuthenticatedUser,
    Depends(require_roles(UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER)),
]