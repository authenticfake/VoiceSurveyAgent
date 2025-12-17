# BEGIN FILE: runs/kit/REQ-006/src/app/shared/exceptions.py
"""
Shared exceptions (REQ-006).

Retrocompatibilità:
- alcuni kit vecchi istanziano InvalidTokenError(message=..., details=...)
- qui accettiamo sia positional che keyword args.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class AppError(Exception):
    message: str = "Application error"
    details: Optional[dict[str, Any]] = None

    def __str__(self) -> str:
        return self.message


class NotFoundError(AppError):
    pass


class ValidationError(AppError):
    pass


class InvalidTokenError(AppError):
    # compat: accetta keyword args
    def __init__(self, message: str = "Invalid token", details: Optional[dict[str, Any]] = None, **_: Any) -> None:
        super().__init__(message=message, details=details)


class TokenExpiredError(AppError):
    def __init__(self, message: str = "Token expired", details: Optional[dict[str, Any]] = None, **_: Any) -> None:
        super().__init__(message=message, details=details)
# END FILE
