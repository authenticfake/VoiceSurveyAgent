"""JWT token validation."""
from datetime import datetime, timezone
from typing import Any, Optional

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.auth.config import AuthConfig
from app.auth.exceptions import ExpiredTokenError, InvalidTokenError
from app.auth.jwks import JWKSClient
from app.auth.models import TokenPayload

class JWTValidator:
    """Validates JWT tokens using JWKS from OIDC provider."""
    
    def __init__(
        self,
        config: AuthConfig,
        jwks_client: JWKSClient
    ) -> None:
        """Initialize JWT validator.
        
        Args:
            config: Authentication configuration
            jwks_client: JWKS client for fetching signing keys
        """
        self._config = config
        self._jwks_client = jwks_client
    
    async def validate_token(
        self,
        token: str,
        verify_exp: bool = True
    ) -> TokenPayload:
        """Validate JWT token and extract payload.
        
        Args:
            token: JWT token string
            verify_exp: Whether to verify expiration
            
        Returns:
            Validated token payload
            
        Raises:
            InvalidTokenError: If token is invalid or malformed
            ExpiredTokenError: If token has expired
        """
        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise InvalidTokenError("Token missing key ID (kid)")
            
            # Get signing key
            signing_key = await self._jwks_client.get_signing_key(kid)
            if not signing_key:
                # Try refreshing JWKS in case of key rotation
                self._jwks_client.clear_cache()
                signing_key = await self._jwks_client.get_signing_key(kid)
                if not signing_key:
                    raise InvalidTokenError(f"Unknown signing key: {kid}")
            
            # Decode and validate token
            options = {
                "verify_exp": verify_exp,
                "verify_aud": True,
                "verify_iss": True,
            }
            
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[self._config.algorithm],
                audience=self._config.client_id,
                issuer=self._config.issuer_url,
                options=options
            )
            
            return self._parse_payload(payload)
            
        except ExpiredSignatureError:
            raise ExpiredTokenError()
        except JWTClaimsError as e:
            raise InvalidTokenError(f"Invalid token claims: {e}")
        except JWTError as e:
            raise InvalidTokenError(f"Token validation failed: {e}")
    
    def _parse_payload(self, payload: dict[str, Any]) -> TokenPayload:
        """Parse JWT payload into TokenPayload model.
        
        Args:
            payload: Raw JWT payload
            
        Returns:
            Parsed token payload
        """
        # Handle exp and iat as timestamps
        exp = payload.get("exp")
        iat = payload.get("iat")
        
        if isinstance(exp, (int, float)):
            exp = datetime.fromtimestamp(exp, tz=timezone.utc)
        if isinstance(iat, (int, float)):
            iat = datetime.fromtimestamp(iat, tz=timezone.utc)
        
        # Extract roles from various claim formats
        roles = []
        if "roles" in payload:
            roles = payload["roles"]
        elif "realm_access" in payload:
            # Keycloak format
            roles = payload["realm_access"].get("roles", [])
        elif "groups" in payload:
            # Some IdPs use groups
            roles = payload["groups"]
        
        return TokenPayload(
            sub=payload["sub"],
            exp=exp,
            iat=iat,
            iss=payload["iss"],
            aud=payload.get("aud", self._config.client_id),
            email=payload.get("email"),
            name=payload.get("name"),
            roles=roles if isinstance(roles, list) else [roles]
        )