"""
Authentication service.

Provides JWT validation and OIDC integration.
"""

from datetime import datetime, timezone

import httpx
import jwt
import structlog
from jwt import PyJWKClient

from app.auth.schemas import TokenPayload, UserRole
from app.config import get_settings
from app.shared.exceptions import AuthenticationError

logger = structlog.get_logger(__name__)
settings = get_settings()


class AuthService:
    """Service for authentication operations."""

    def __init__(self) -> None:
        """Initialize auth service."""
        self._jwks_client: PyJWKClient | None = None

    async def _get_jwks_client(self) -> PyJWKClient:
        """Get or create JWKS client for token validation."""
        if self._jwks_client is None:
            jwks_uri = f"{settings.oidc_issuer_url}/.well-known/jwks.json"
            self._jwks_client = PyJWKClient(jwks_uri)
        return self._jwks_client

    async def validate_token(self, token: str) -> TokenPayload:
        """Validate JWT token and extract payload."""
        try:
            # Get signing key from JWKS
            jwks_client = await self._get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=settings.oidc_client_id,
                issuer=settings.oidc_issuer_url,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            # Extract role from claims
            role = self._extract_role(payload)

            return TokenPayload(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                iss=payload.get("iss"),
                aud=payload.get("aud"),
                email=payload.get("email"),
                name=payload.get("name"),
                role=role,
            )

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise AuthenticationError(message="Token has expired")
        except jwt.InvalidAudienceError:
            logger.warning("Invalid token audience")
            raise AuthenticationError(message="Invalid token audience")
        except jwt.InvalidIssuerError:
            logger.warning("Invalid token issuer")
            raise AuthenticationError(message="Invalid token issuer")
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token", error=str(e))
            raise AuthenticationError(message="Invalid token")
        except Exception as e:
            logger.error("Token validation failed", error=str(e))
            raise AuthenticationError(message="Token validation failed")

    def _extract_role(self, payload: dict) -> UserRole | None:
        """Extract user role from token claims."""
        # Check common claim locations for role
        role_claim = settings.oidc_role_claim

        # Try direct claim
        role_value = payload.get(role_claim)

        # Try nested in realm_access (Keycloak style)
        if not role_value and "realm_access" in payload:
            roles = payload["realm_access"].get("roles", [])
            role_value = self._map_roles_to_app_role(roles)

        # Try nested in resource_access (Keycloak style)
        if not role_value and "resource_access" in payload:
            client_roles = payload["resource_access"].get(
                settings.oidc_client_id, {}
            ).get("roles", [])
            role_value = self._map_roles_to_app_role(client_roles)

        # Map to UserRole enum
        if role_value:
            try:
                return UserRole(role_value.lower())
            except ValueError:
                logger.warning(
                    "Unknown role in token",
                    role=role_value,
                )

        return None

    def _map_roles_to_app_role(self, roles: list[str]) -> str | None:
        """Map IdP roles to application role."""
        # Priority order: admin > campaign_manager > viewer
        role_priority = ["admin", "campaign_manager", "viewer"]
        
        for role in role_priority:
            if role in [r.lower() for r in roles]:
                return role
        
        return None