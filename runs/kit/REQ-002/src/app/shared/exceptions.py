"""Custom exception classes for the application."""

from typing import Any

class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class AuthenticationError(AppException):
    """Authentication-related errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTH_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details)

class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    def __init__(self, message: str = "Token has expired") -> None:
        super().__init__(message, "TOKEN_EXPIRED")

class TokenInvalidError(AuthenticationError):
    """Token is invalid."""

    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message, "TOKEN_INVALID")

class OIDCError(AuthenticationError):
    """OIDC-specific errors."""

    def __init__(
        self,
        message: str = "OIDC error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, "OIDC_ERROR", details)

class AuthorizationError(AppException):
    """Authorization-related errors."""

    def __init__(
        self,
        message: str = "Access denied",
        code: str = "AUTHZ_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details)

class InsufficientPermissionsError(AuthorizationError):
    """User lacks required permissions."""

    def __init__(
        self,
        required_role: str,
        user_role: str | None = None,
    ) -> None:
        details = {"required_role": required_role}
        if user_role:
            details["user_role"] = user_role
        super().__init__(
            f"Insufficient permissions. Required role: {required_role}",
            "INSUFFICIENT_PERMISSIONS",
            details,
        )

class NotFoundError(AppException):
    """Resource not found."""

    def __init__(
        self,
        resource: str,
        identifier: str | None = None,
    ) -> None:
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        super().__init__(message, "NOT_FOUND", {"resource": resource})

class ValidationError(AppException):
    """Validation error."""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message, "VALIDATION_ERROR", {"errors": errors or []})