from fastapi import Depends, HTTPException, status

from app.auth.domain.models import Role, UserPrincipal


async def get_current_user() -> UserPrincipal:
    raise RuntimeError(
        "OIDC authentication is not configured. "
        "Override `get_current_user` dependency with REQ-001 implementation."
    )


def require_roles(*roles: Role):
    async def _authorizer(
        user: UserPrincipal = Depends(get_current_user),
    ) -> UserPrincipal:
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "forbidden", "message": "Insufficient role privileges"},
            )
        return user

    return _authorizer