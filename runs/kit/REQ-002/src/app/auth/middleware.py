"""JWT authentication middleware for FastAPI."""
import logging
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.auth.config import AuthConfig
from app.auth.exceptions import AuthenticationError, ExpiredTokenError, InvalidTokenError
from app.auth.jwt_validator import JWTValidator
from app.auth.jwks import JWKSClient

logger = logging.getLogger(__name__)

class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT token validation on protected routes."""
    
    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/auth/login",
        "/api/auth/callback",
        "/api/auth/refresh",
        "/webhooks/telephony/events",
    }
    
    # Path prefixes that don't require authentication
    PUBLIC_PREFIXES = (
        "/static/",
        "/api/auth/",
    )
    
    def __init__(
        self,
        app,
        config: AuthConfig,
        jwt_validator: Optional[JWTValidator] = None
    ) -> None:
        """Initialize JWT auth middleware.
        
        Args:
            app: FastAPI application
            config: Authentication configuration
            jwt_validator: Optional JWT validator (created if not provided)
        """
        super().__init__(app)
        self._config = config
        
        if jwt_validator:
            self._jwt_validator = jwt_validator
        else:
            jwks_client = JWKSClient(config.jwks_uri)
            self._jwt_validator = JWTValidator(config, jwks_client)
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and validate JWT if required.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response from handler or error response
        """
        # Skip auth for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Skip auth if OIDC not configured (development mode)
        if not self._config.is_configured():
            logger.warning(
                "OIDC not configured, skipping authentication for %s",
                request.url.path
            )
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return self._unauthorized_response(
                "missing_token",
                "Authorization header required"
            )
        
        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return self._unauthorized_response(
                "invalid_header",
                "Authorization header must be 'Bearer <token>'"
            )
        
        token = parts[1]
        
        try:
            # Validate token
            payload = await self._jwt_validator.validate_token(token)
            
            # Store payload in request state for later use
            request.state.token_payload = payload
            request.state.user_sub = payload.sub
            
            return await call_next(request)
            
        except ExpiredTokenError:
            return self._unauthorized_response(
                "token_expired",
                "Token has expired"
            )
        except InvalidTokenError as e:
            return self._unauthorized_response(
                "invalid_token",
                str(e)
            )
        except Exception as e:
            logger.exception("Unexpected error during token validation")
            return self._unauthorized_response(
                "authentication_error",
                "Authentication failed"
            )
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required).
        
        Args:
            path: Request path
            
        Returns:
            True if path is public
        """
        if path in self.PUBLIC_PATHS:
            return True
        
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _unauthorized_response(
        self,
        error: str,
        description: str
    ) -> JSONResponse:
        """Create 401 unauthorized response.
        
        Args:
            error: Error code
            description: Error description
            
        Returns:
            JSON response with 401 status
        """
        return JSONResponse(
            status_code=401,
            content={
                "error": error,
                "error_description": description
            },
            headers={
                "WWW-Authenticate": 'Bearer realm="voicesurveyagent"'
            }
        )