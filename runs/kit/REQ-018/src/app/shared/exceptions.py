"""
Custom exceptions for the application.

REQ-018: Campaign CSV export
"""

from typing import Any, Optional
from uuid import UUID


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found exception."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[UUID | str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message=message, code="NOT_FOUND", details=details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ValidationError(AppException):
    """Validation error exception."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="VALIDATION_ERROR", details=details)
        self.field = field


class AuthorizationError(AppException):
    """Authorization error exception."""

    def __init__(
        self,
        message: str = "Access denied",
        required_role: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="AUTHORIZATION_ERROR", details=details)
        self.required_role = required_role


class ExportError(AppException):
    """Export operation error exception."""

    def __init__(
        self,
        message: str,
        job_id: Optional[UUID] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="EXPORT_ERROR", details=details)
        self.job_id = job_id


class StorageError(AppException):
    """Storage operation error exception."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="STORAGE_ERROR", details=details)
        self.operation = operation