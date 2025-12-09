"""OIDC client for authorization code flow."""
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.auth.config import AuthConfig
from app.auth.exceptions import OIDCProviderError
from app.auth.models import TokenResponse, UserInfo

class OIDCClient:
    """Client for OIDC authorization code flow."""
    
    def __init__(
        self,
        config: AuthConfig,
        http_timeout: float = 10.0
    ) -> None:
        """Initialize OIDC client.
        
        Args:
            config: Authentication configuration
            http_timeout: HTTP request timeout
        """
        self._config = config
        self._http_timeout = http_timeout
    
    def generate_state(self) -> str:
        """Generate a cryptographically secure state parameter.
        
        Returns:
            Random state string
        """
        return secrets.token_urlsafe(32)
    
    def get_authorization_url(
        self,
        state: str,
        redirect_uri: Optional[str] = None,
        nonce: Optional[str] = None
    ) -> str:
        """Build authorization URL for OIDC flow.
        
        Args:
            state: CSRF state parameter
            redirect_uri: Optional custom redirect URI
            nonce: Optional nonce for ID token validation
            
        Returns:
            Authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": self._config.client_id,
            "redirect_uri": redirect_uri or self._config.redirect_uri,
            "scope": " ".join(self._config.scopes),
            "state": state,
        }
        
        if nonce:
            params["nonce"] = nonce
        
        return f"{self._config.authorization_endpoint}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        code: str,
        redirect_uri: Optional[str] = None
    ) -> TokenResponse:
        """Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            redirect_uri: Redirect URI used in authorization request
            
        Returns:
            Token response with access token and optional refresh token
            
        Raises:
            OIDCProviderError: If token exchange fails
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri or self._config.redirect_uri,
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
        }
        
        try:
            async with httpx.AsyncClient(
                timeout=self._http_timeout
            ) as client:
                response = await client.post(
                    self._config.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    raise OIDCProviderError(
                        f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}"
                    )
                
                return TokenResponse(**response.json())
        except httpx.HTTPError as e:
            raise OIDCProviderError(f"HTTP error during token exchange: {e}")
    
    async def refresh_tokens(
        self,
        refresh_token: str
    ) -> TokenResponse:
        """Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New token response
            
        Raises:
            OIDCProviderError: If refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
        }
        
        try:
            async with httpx.AsyncClient(
                timeout=self._http_timeout
            ) as client:
                response = await client.post(
                    self._config.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    raise OIDCProviderError(
                        f"Token refresh failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}"
                    )
                
                return TokenResponse(**response.json())
        except httpx.HTTPError as e:
            raise OIDCProviderError(f"HTTP error during token refresh: {e}")
    
    async def get_userinfo(
        self,
        access_token: str
    ) -> UserInfo:
        """Fetch user info from OIDC provider.
        
        Args:
            access_token: Valid access token
            
        Returns:
            User information
            
        Raises:
            OIDCProviderError: If userinfo request fails
        """
        try:
            async with httpx.AsyncClient(
                timeout=self._http_timeout
            ) as client:
                response = await client.get(
                    self._config.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code != 200:
                    raise OIDCProviderError(
                        f"Userinfo request failed with status {response.status_code}"
                    )
                
                return UserInfo(**response.json())
        except httpx.HTTPError as e:
            raise OIDCProviderError(f"HTTP error during userinfo request: {e}")