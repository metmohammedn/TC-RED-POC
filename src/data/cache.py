"""
Redis cache wrapper — optional, app runs without it.
"""
import json
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_cache = None


class CacheManager:
    """Simple Redis cache with graceful degradation."""

    def __init__(self, redis_url: str):
        import redis
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._available = True
        try:
            self._redis.ping()
            logger.info("Redis connection established")
        except Exception as e:
            self._available = False
            logger.warning("Redis unavailable — caching disabled: %s", e)

    def get(self, key: str) -> Optional[Any]:
        if not self._available:
            return None
        try:
            val = self._redis.get(key)
            return json.loads(val) if val else None
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        if not self._available:
            return False
        try:
            self._redis.setex(key, ttl_seconds, json.dumps(value, default=str))
            return True
        except Exception:
            return False

    def get_or_set(self, key: str, factory: Callable, ttl_seconds: int = 3600) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl_seconds)
        return value


def init_cache(redis_url: str) -> CacheManager:
    global _cache
    _cache = CacheManager(redis_url)
    return _cache


def get_cache() -> CacheManager:
    if _cache is None:
        raise RuntimeError("Cache not initialized. Call init_cache() first.")
    return _cache
