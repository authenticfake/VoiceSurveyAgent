# BEGIN FILE: runs/kit/REQ-006/src/app/auth/rbac.py
"""
RBAC (REQ-006 shadow).

Evita l'import di REQ-003 e usa CurrentUser.role dai test headers.
"""

from __future__ import annotations

from typing import Annotated, Iterable

from fastapi import Depends, HTTPException, status

from app.auth.middleware import CurrentUser, get_current_user


def _has_any_role(user_role: str, allowed: Iterable[str]) -> bool:
    return user_role in set(allowed)


def require_roles(*roles: str):
    async def _dep(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if not _has_any_role(user.role, roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dep


# richiesto dal router contatti
require_campaign_manager = require_roles("campaign_manager", "admin")
# END FILE
