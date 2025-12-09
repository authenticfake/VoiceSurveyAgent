"""
Admin configuration module.

REQ-019: Admin configuration API
"""

from app.admin.router import router as admin_router
from app.admin.service import AdminConfigService
from app.admin.schemas import (
    AdminConfigResponse,
    AdminConfigUpdate,
    TelephonyConfigUpdate,
    LLMConfigUpdate,
    EmailConfigUpdate,
    RetentionConfigUpdate,
)

__all__ = [
    "admin_router",
    "AdminConfigService",
    "AdminConfigResponse",
    "AdminConfigUpdate",
    "TelephonyConfigUpdate",
    "LLMConfigUpdate",
    "EmailConfigUpdate",
    "RetentionConfigUpdate",
]