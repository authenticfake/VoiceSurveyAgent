from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass
from typing import Any, Dict

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@dataclass(slots=True)
class CachedJWKS:
    keys: Dict[str, dict]
    fetched_at: float


class JWKSCache:
    """Caches JWKS keys for configurable TTL to avoid excessive HTTP calls."""

    def __init__(self, jwks_url: str, ttl_seconds: int = 300):
        self._jwks_url = jwks_url
        self._ttl_seconds = ttl_seconds
        self._cache: CachedJWKS | None = None
        self._lock = asyncio.Lock()

    async def get_key(self, kid: str) -> dict | None:
        async with self._lock:
            if not self._cache or (time.time() - self._cache.fetched_at) > self._ttl_seconds:
                await self._refresh()
            return self._cache.keys.get(kid) if self._cache else None

    async def _refresh(self) -> None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(self._jwks_url)
            response.raise_for_status()
            payload = response.json()
            keys = {key["kid"]: key for key in payload.get("keys", [])}
            self._cache = CachedJWKS(keys=keys, fetched_at=time.time())


def jwk_to_pem(key_dict: dict) -> bytes:
    """Convert an RSA JWK entry to PEM bytes for verification."""
    if key_dict.get("kty") != "RSA":
        raise ValueError("Only RSA keys are supported")
    n_int = int.from_bytes(_b64_to_bytes(key_dict["n"]), "big")
    e_int = int.from_bytes(_b64_to_bytes(key_dict["e"]), "big")
    public_numbers = rsa.RSAPublicNumbers(e_int, n_int)
    public_key = public_numbers.public_key()
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _b64_to_bytes(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)