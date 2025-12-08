"""Custom exception classes for the application."""

from typing import Any, Optional

class AppError(Exception):
    """Base application error."""
    
    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize error.
        
        Args:
            message: Error message
            details: Optional additional details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

class NotFoundError(AppError):
    """Resource not found error."""
    pass

class ValidationError(AppError):
    """Validation error."""
    pass

class StateTransitionError(AppError):
    """Invalid state transition error."""
    pass

class AuthenticationError(AppError):
    """Authentication error."""
    pass

class AuthorizationError(AppError):
    """Authorization error."""
    pass