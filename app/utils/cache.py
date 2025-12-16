"""Simple in-memory cache with TTL"""
import time
from typing import Any, Optional
from functools import wraps

class SimpleCache:
    """Thread-safe in-memory cache with TTL"""

    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            value, expire_time = self._cache[key]
            if time.time() < expire_time:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set value with TTL in seconds"""
        self._cache[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        """Delete a key from cache"""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching pattern (simple prefix match)"""
        keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
        for key in keys_to_delete:
            del self._cache[key]

# Global cache instance
cache = SimpleCache()

# Cache keys
CACHE_LINKS_ALL = "links:all"
CACHE_LINKS_PUBLIC = "links:public"
CACHE_SETTINGS = "settings"

def invalidate_links_cache():
    """Invalidate all links-related cache"""
    cache.invalidate_pattern("links:")

def invalidate_settings_cache():
    """Invalidate settings cache"""
    cache.delete(CACHE_SETTINGS)
