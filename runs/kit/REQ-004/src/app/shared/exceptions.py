"""
Custom exception classes for the application.

Provides structured error handling with HTTP status code mapping.
"""

from typing import Any

class AppException(Exception):
    """Base application exception."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An internal error occurred"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

class ValidationError(AppException):
    """Validation error exception."""

    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"

class AuthenticationError(AppException):
    """Authentication error exception."""

    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication failed"

class AuthorizationError(AppException):
    """Authorization error exception."""

    status_code = 403
    error_code = "AUTHORIZATION_ERROR"
    message = "Access denied"

class NotFoundError(AppException):
    """Resource not found exception."""

    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"

class ConflictError(AppException):
    """Resource conflict exception."""

    status_code = 409
    error_code = "CONFLICT"
    message = "Resource conflict"

class InvalidStateTransitionError(AppException):
    """Invalid state transition exception."""

    status_code = 400
    error_code = "INVALID_STATE_TRANSITION"
    message = "Invalid state transition"