class AuthError(Exception):
    """Base authentication error."""


class AuthenticationError(AuthError):
    """Raised when authentication cannot be completed."""


class AuthorizationError(AuthError):
    """Raised when role checks fail."""


class OIDCConfigurationError(AuthError):
    """Raised when OIDC configuration is invalid or incomplete."""