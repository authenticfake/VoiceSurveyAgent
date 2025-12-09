"""JWKS (JSON Web Key Set) management for JWT validation."""
import time
from typing import Any, Optional

import httpx
from jose import jwk
from jose.backends.base import Key

class JWKSClient:
    """Client for fetching and caching JWKS from OIDC provider."""
    
    def __init__(
        self,
        jwks_uri: str,
        cache_ttl_seconds: int = 3600,
        http_timeout: float = 10.0
    ) -> None:
        """Initialize JWKS client.
        
        Args:
            jwks_uri: URI to fetch JWKS from
            cache_ttl_seconds: How long to cache JWKS
            http_timeout: HTTP request timeout
        """
        self._jwks_uri = jwks_uri
        self._cache_ttl = cache_ttl_seconds
        self._http_timeout = http_timeout
        self._keys: dict[str, Key] = {}
        self._last_fetch: float = 0
    
    async def get_signing_key(self, kid: str) -> Optional[Key]:
        """Get signing key by key ID.
        
        Args:
            kid: Key ID from JWT header
            
        Returns:
            Signing key if found, None otherwise
        """
        await self._refresh_if_needed()
        return self._keys.get(kid)
    
    async def get_signing_keys(self) -> dict[str, Key]:
        """Get all signing keys.
        
        Returns:
            Dictionary of key ID to signing key
        """
        await self._refresh_if_needed()
        return self._keys.copy()
    
    async def _refresh_if_needed(self) -> None:
        """Refresh JWKS cache if expired."""
        now = time.time()
        if now - self._last_fetch < self._cache_ttl and self._keys:
            return
        
        await self._fetch_jwks()
    
    async def _fetch_jwks(self) -> None:
        """Fetch JWKS from provider."""
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            response = await client.get(self._jwks_uri)
            response.raise_for_status()
            jwks_data = response.json()
        
        self._keys = {}
        for key_data in jwks_data.get("keys", []):
            if key_data.get("use") == "sig" or "use" not in key_data:
                kid = key_data.get("kid")
                if kid:
                    self._keys[kid] = jwk.construct(key_data)
        
        self._last_fetch = time.time()
    
    def clear_cache(self) -> None:
        """Clear the JWKS cache."""
        self._keys = {}
        self._last_fetch = 0