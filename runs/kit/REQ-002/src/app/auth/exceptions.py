"""Authentication exceptions."""
from typing import Optional

class AuthenticationError(Exception):
    """Base authentication error."""
    
    def __init__(
        self,
        error: str,
        description: str,
        status_code: int = 401
    ) -> None:
        """Initialize authentication error."""
        self.error = error
        self.description = description
        self.status_code = status_code
        super().__init__(description)

class InvalidTokenError(AuthenticationError):
    """Invalid or malformed token error."""
    
    def __init__(
        self,
        description: str = "Invalid or malformed token"
    ) -> None:
        """Initialize invalid token error."""
        super().__init__(
            error="invalid_token",
            description=description,
            status_code=401
        )

class ExpiredTokenError(AuthenticationError):
    """Expired token error."""
    
    def __init__(
        self,
        description: str = "Token has expired"
    ) -> None:
        """Initialize expired token error."""
        super().__init__(
            error="token_expired",
            description=description,
            status_code=401
        )

class InsufficientScopeError(AuthenticationError):
    """Insufficient scope/permissions error."""
    
    def __init__(
        self,
        description: str = "Insufficient permissions"
    ) -> None:
        """Initialize insufficient scope error."""
        super().__init__(
            error="insufficient_scope",
            description=description,
            status_code=403
        )

class OIDCProviderError(AuthenticationError):
    """OIDC provider communication error."""
    
    def __init__(
        self,
        description: str = "OIDC provider error"
    ) -> None:
        """Initialize OIDC provider error."""
        super().__init__(
            error="provider_error",
            description=description,
            status_code=502
        )

class InvalidStateError(AuthenticationError):
    """Invalid CSRF state error."""
    
    def __init__(
        self,
        description: str = "Invalid state parameter"
    ) -> None:
        """Initialize invalid state error."""
        super().__init__(
            error="invalid_state",
            description=description,
            status_code=400
        )