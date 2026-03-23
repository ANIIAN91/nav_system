"""Cache backend abstractions and helpers."""

import time
from typing import Any, Optional, Protocol


class CacheBackend(Protocol):
    """Boundary for cache storage backends."""

    def get(self, key: str) -> Optional[Any]:
        """Get a cached value if it is still valid."""

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Store a cached value for a bounded TTL."""

    def delete(self, key: str) -> None:
        """Delete a cached key."""

    def clear(self) -> None:
        """Clear the full backend."""

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate keys by prefix."""


class InMemoryCacheBackend:
    """Thread-safe in-memory cache with TTL."""

    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, expire_time = self._cache[key]
            if time.time() < expire_time:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set value with TTL in seconds."""
        self._cache[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        """Delete a key from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching a prefix pattern."""
        keys_to_delete = [key for key in self._cache if key.startswith(pattern)]
        for key in keys_to_delete:
            del self._cache[key]


class CacheProxy:
    """Proxy that always resolves the current cache backend."""

    def get(self, key: str) -> Optional[Any]:
        return get_cache_backend().get(key)

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        get_cache_backend().set(key, value, ttl=ttl)

    def delete(self, key: str) -> None:
        get_cache_backend().delete(key)

    def clear(self) -> None:
        get_cache_backend().clear()

    def invalidate_pattern(self, pattern: str) -> None:
        get_cache_backend().invalidate_pattern(pattern)


_cache_backend: CacheBackend = InMemoryCacheBackend()
cache = CacheProxy()

CACHE_LINKS_ALL = "links:all"
CACHE_LINKS_PUBLIC = "links:public"
CACHE_SETTINGS = "settings"


def get_cache_backend() -> CacheBackend:
    """Return the active cache backend."""
    return _cache_backend


def set_cache_backend(backend: CacheBackend) -> None:
    """Replace the active cache backend."""
    global _cache_backend
    _cache_backend = backend


def reset_cache_backend() -> None:
    """Restore the default in-memory cache backend."""
    set_cache_backend(InMemoryCacheBackend())


def invalidate_links_cache() -> None:
    """Invalidate all links-related cache."""
    cache.invalidate_pattern("links:")


def get_cached_settings() -> Optional[dict]:
    """Get cached site settings."""
    cached = cache.get(CACHE_SETTINGS)
    return dict(cached) if cached is not None else None


def set_cached_settings(settings_value: dict, ttl: int = 60) -> None:
    """Cache site settings."""
    cache.set(CACHE_SETTINGS, dict(settings_value), ttl=ttl)


def invalidate_settings_cache() -> None:
    """Invalidate settings cache."""
    cache.delete(CACHE_SETTINGS)
