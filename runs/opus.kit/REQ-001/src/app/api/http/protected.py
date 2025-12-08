"""Example protected routes demonstrating RBAC."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import RequireAdmin, RequireReader, RequireWriter, get_current_user
from app.auth.domain import User, UserResponse, UserRole

router = APIRouter(prefix="/protected", tags=["protected"])


@router.get("/viewer-resource")
async def viewer_resource(
    current_user: Annotated[User, RequireReader],
) -> dict[str, str]:
    """
    Resource accessible by all authenticated users (viewer, campaign_manager, admin).
    """
    return {
        "message": "You have read access",
        "user_role": current_user.role.value,
    }


@router.get("/writer-resource")
async def writer_resource(
    current_user: Annotated[User, RequireWriter],
) -> dict[str, str]:
    """
    Resource accessible by campaign_manager and admin roles.
    """
    return {
        "message": "You have write access",
        "user_role": current_user.role.value,
    }


@router.get("/admin-resource")
async def admin_resource(
    current_user: Annotated[User, RequireAdmin],
) -> dict[str, str]:
    """
    Resource accessible only by admin role.
    """
    return {
        "message": "You have admin access",
        "user_role": current_user.role.value,
    }


@router.get("/my-permissions")
async def get_my_permissions(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    """
    Get current user's permissions based on role.
    """
    from app.auth.domain import RBACPolicy

    return {
        "user": UserResponse.model_validate(current_user).model_dump(),
        "permissions": {
            "can_read": RBACPolicy.can_read(current_user.role),
            "can_write": RBACPolicy.can_write(current_user.role),
            "is_admin": RBACPolicy.is_admin(current_user.role),
        },
    }