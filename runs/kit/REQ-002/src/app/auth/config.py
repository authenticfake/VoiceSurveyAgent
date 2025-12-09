"""Authentication configuration from environment variables."""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class AuthConfig:
    """OIDC and JWT configuration settings."""
    
    # OIDC Provider endpoints
    issuer_url: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    
    # Client credentials
    client_id: str
    client_secret: str
    
    # Redirect URIs
    redirect_uri: str
    post_logout_redirect_uri: str
    
    # Token settings
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    
    # Algorithm for JWT
    algorithm: str
    
    # Optional: custom scopes
    scopes: list[str]
    
    @classmethod
    def from_env(cls) -> "AuthConfig":
        """Load configuration from environment variables."""
        return cls(
            issuer_url=os.environ.get("OIDC_ISSUER_URL", ""),
            authorization_endpoint=os.environ.get(
                "OIDC_AUTHORIZATION_ENDPOINT",
                ""
            ),
            token_endpoint=os.environ.get("OIDC_TOKEN_ENDPOINT", ""),
            userinfo_endpoint=os.environ.get("OIDC_USERINFO_ENDPOINT", ""),
            jwks_uri=os.environ.get("OIDC_JWKS_URI", ""),
            client_id=os.environ.get("OIDC_CLIENT_ID", ""),
            client_secret=os.environ.get("OIDC_CLIENT_SECRET", ""),
            redirect_uri=os.environ.get(
                "OIDC_REDIRECT_URI",
                "http://localhost:8000/api/auth/callback"
            ),
            post_logout_redirect_uri=os.environ.get(
                "OIDC_POST_LOGOUT_REDIRECT_URI",
                "http://localhost:8000"
            ),
            access_token_expire_minutes=int(
                os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
            ),
            refresh_token_expire_days=int(
                os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7")
            ),
            algorithm=os.environ.get("JWT_ALGORITHM", "RS256"),
            scopes=os.environ.get(
                "OIDC_SCOPES",
                "openid profile email"
            ).split(),
        )
    
    def is_configured(self) -> bool:
        """Check if OIDC is properly configured."""
        return bool(
            self.issuer_url
            and self.client_id
            and self.jwks_uri
        )