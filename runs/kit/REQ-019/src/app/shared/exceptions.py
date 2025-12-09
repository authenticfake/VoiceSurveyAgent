"""
Shared exception definitions.

REQ-019: Admin configuration API
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="NOT_FOUND", status_code=404, details=details)


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=400, details=details)


class AuthorizationError(AppException):
    """Authorization error."""

    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="AUTHORIZATION_ERROR", status_code=403, details=details)


class AuthenticationError(AppException):
    """Authentication error."""

    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="AUTHENTICATION_ERROR", status_code=401, details=details)


class ConfigurationError(AppException):
    """Configuration error."""

    def __init__(self, message: str = "Configuration error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="CONFIGURATION_ERROR", status_code=500, details=details)


class SecretsManagerError(AppException):
    """AWS Secrets Manager error."""

    def __init__(self, message: str = "Secrets Manager error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="SECRETS_MANAGER_ERROR", status_code=500, details=details)