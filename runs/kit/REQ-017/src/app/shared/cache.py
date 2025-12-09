"""
Redis cache client for stats caching.

REQ-017: Campaign dashboard stats API
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from app.shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheClient:
    """Redis cache client with JSON serialization."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._client is None:
            self._client = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self._client is None:
            await self.connect()
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Set value in cache with TTL."""
        if self._client is None:
            await self.connect()
        try:
            serialized = json.dumps(value, default=str)
            await self._client.setex(key, ttl_seconds, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if self._client is None:
            await self.connect()
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False


# Global cache client instance
_cache_client: Optional[CacheClient] = None


def get_cache_client() -> CacheClient:
    """Get or create cache client instance."""
    global _cache_client
    if _cache_client is None:
        _cache_client = CacheClient(settings.redis_url)
    return _cache_client