"""
Custom exception classes.

Provides domain-specific exceptions with structured error information.
"""

from typing import Any


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize application error."""
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AppError):
    """Authentication failed error."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize authentication error."""
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details,
        )


class AuthorizationError(AppError):
    """Authorization denied error."""

    def __init__(
        self,
        message: str = "Access denied",
        required_role: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize authorization error."""
        error_details = details or {}
        if required_role:
            error_details["required_role"] = required_role
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
            details=error_details,
        )


class ConfigurationError(AppError):
    """Configuration error."""

    def __init__(
        self,
        message: str = "Configuration error",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize configuration error."""
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=500,
            details=details,
        )


class NotFoundError(AppError):
    """Resource not found error."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize not found error."""
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=error_details,
        )


class ValidationError(AppError):
    """Validation error."""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: list[dict[str, Any]] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize validation error."""
        error_details = details or {}
        if errors:
            error_details["errors"] = errors
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=error_details,
        )


class ConflictError(AppError):
    """Resource conflict error."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize conflict error."""
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details,
        )