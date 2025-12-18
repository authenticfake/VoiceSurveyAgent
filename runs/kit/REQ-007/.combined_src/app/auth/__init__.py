"""
Auth package.

Keep __init__ lightweight to avoid import-time side effects.
Import concrete components from submodules, e.g.:
  - from app.auth.middleware import AuthMiddleware
  - from app.auth.service import AuthService
"""

from app.auth.models import Base, User  # re-export the ORM base + user model

__all__ = ["Base", "User"]
