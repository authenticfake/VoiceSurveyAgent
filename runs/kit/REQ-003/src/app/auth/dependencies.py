"""
Authentication and authorization dependencies.

Provides FastAPI dependencies for route protection.
"""

from typing import Annotated

from fastapi import Depends

from app.auth.middleware import CurrentUser, get_current_user
from app.auth.rbac import (
    Permission,
    RBACChecker,
    require_admin,
    require_all_permissions,
    require_any_permission,
    require_campaign_manager,
    require_permission,
    require_viewer,
)

# Re-export for convenience
__all__ = [
    "CurrentUser",
    "get_current_user",
    "Permission",
    "RBACChecker",
    "require_admin",
    "require_campaign_manager",
    "require_viewer",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "AdminRequired",
    "CampaignManagerRequired",
    "ViewerRequired",
]

# Type aliases for common dependency patterns
AdminRequired = Annotated[None, Depends(require_admin())]
CampaignManagerRequired = Annotated[None, Depends(require_campaign_manager())]
ViewerRequired = Annotated[None, Depends(require_viewer())]