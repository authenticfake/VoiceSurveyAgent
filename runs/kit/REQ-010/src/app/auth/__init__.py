"""
Authentication module.

REQ-002: OIDC authentication integration
REQ-003: RBAC authorization middleware
REQ-010: Telephony webhook handler (reuses models)
"""

from app.auth.models import Base, User, UserRole

__all__ = [
    "Base",
    "User",
    "UserRole",
]