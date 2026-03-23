"""Rate limit service abstractions."""

import time
from collections import defaultdict
from typing import Protocol

from app.config import get_settings


class RateLimiter(Protocol):
    """Boundary for login rate limiting."""

    def check(self, key: str) -> tuple[bool, int]:
        """Return whether the caller is allowed and remaining lockout seconds."""

    def record_failure(self, key: str) -> None:
        """Record a failed attempt for a caller."""

    def clear(self, key: str) -> None:
        """Clear state for a caller after success."""


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for login attempts."""

    def __init__(self, max_attempts: int, window_seconds: int, lockout_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._lockouts: dict[str, float] = {}

    def check(self, key: str) -> tuple[bool, int]:
        now = time.time()
        self._prune_attempts(key, now)
        lockout_until = self._lockouts.get(key, 0)
        if lockout_until > now:
            return False, int(lockout_until - now)
        if key in self._lockouts:
            self._lockouts.pop(key, None)
        return True, 0

    def record_failure(self, key: str) -> None:
        now = time.time()
        self._prune_attempts(key, now)
        self._attempts[key].append(now)
        if len(self._attempts[key]) >= self.max_attempts:
            self._lockouts[key] = now + self.lockout_seconds

    def clear(self, key: str) -> None:
        self._attempts.pop(key, None)
        self._lockouts.pop(key, None)

    def clear_all(self) -> None:
        """Helper for tests."""
        self._attempts.clear()
        self._lockouts.clear()

    def _prune_attempts(self, key: str, now: float) -> None:
        self._attempts[key] = [stamp for stamp in self._attempts[key] if now - stamp < self.window_seconds]
        if not self._attempts[key]:
            self._attempts.pop(key, None)


class RateLimiterProxy:
    """Proxy that always resolves the current rate-limit backend."""

    def check(self, key: str) -> tuple[bool, int]:
        return get_rate_limiter_backend().check(key)

    def record_failure(self, key: str) -> None:
        get_rate_limiter_backend().record_failure(key)

    def clear(self, key: str) -> None:
        get_rate_limiter_backend().clear(key)

    def clear_all(self) -> None:
        backend = get_rate_limiter_backend()
        if hasattr(backend, "clear_all"):
            backend.clear_all()


def build_in_memory_rate_limiter() -> InMemoryRateLimiter:
    """Build the default in-memory rate limiter from app settings."""
    settings = get_settings()
    return InMemoryRateLimiter(
        max_attempts=settings.max_login_attempts,
        window_seconds=settings.login_window_seconds,
        lockout_seconds=settings.lockout_seconds,
    )


_rate_limiter_backend: RateLimiter = build_in_memory_rate_limiter()
_rate_limiter_proxy = RateLimiterProxy()


def get_rate_limiter_backend() -> RateLimiter:
    """Return the active rate-limit backend."""
    return _rate_limiter_backend


def set_rate_limiter(rate_limiter: RateLimiter) -> None:
    """Replace the active rate-limit backend."""
    global _rate_limiter_backend
    _rate_limiter_backend = rate_limiter


def reset_rate_limiter() -> None:
    """Restore the default in-memory rate limiter."""
    set_rate_limiter(build_in_memory_rate_limiter())


def get_rate_limiter() -> RateLimiter:
    """Return the default login rate limiter proxy."""
    return _rate_limiter_proxy
