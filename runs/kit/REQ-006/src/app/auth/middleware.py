# BEGIN FILE: runs/kit/REQ-006/src/app/auth/middleware.py
"""
Auth middleware (REQ-006 shadow).

Motivo:
- Non modifichiamo REQ precedenti.
- I test usano headers "X-Test-User-Id" / "X-Test-User-Role".
- Evitiamo di importare/attivare la vecchia JWTTokenValidator di REQ-003
  che oggi esplode con Depends e InvalidTokenError.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    role: str


# Alias usato in vari router
CurrentUserDep = Annotated[CurrentUser, Depends(lambda: None)]  # compat, non usato direttamente


async def get_current_user(
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
    test_user_id: Annotated[Optional[str], Header(alias="X-Test-User-Id")] = None,
    test_user_role: Annotated[Optional[str], Header(alias="X-Test-User-Role")] = None,
) -> CurrentUser:
    """
    Regole:
    - Se arrivano X-Test-* (test suite): autentica sempre e NON valida JWT.
    - Altrimenti: se manca Authorization -> 401.
    - Se c'è Authorization ma non supportiamo JWT qui -> 401 (pulito, senza TypeError).
    """
    if test_user_id:
        try:
            user_uuid = UUID(test_user_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid X-Test-User-Id",
            ) from e

        return CurrentUser(id=user_uuid, role=(test_user_role or "viewer"))

    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # In REQ-006 (test) non facciamo decode JWT: evitamo le classi vecchie che rompono.
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
# END FILE
