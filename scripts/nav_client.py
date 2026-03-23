"""Shared Nav System API client helpers."""

from __future__ import annotations

from typing import Any

import httpx

API_PREFIX = "/api/v1"


class NavClientError(RuntimeError):
    """Raised when the Nav System API returns an error."""


def normalize_api_path(path: str) -> str:
    """Normalize an endpoint path."""
    return path if path.startswith("/") else f"/{path}"


def build_api_url(base_url: str, path: str) -> str:
    """Build an absolute API URL from either site root or API base."""
    base = base_url.rstrip("/")
    normalized_path = normalize_api_path(path)
    if base.endswith(API_PREFIX):
        suffix = normalized_path[len(API_PREFIX) :] if normalized_path.startswith(API_PREFIX) else normalized_path
        return f"{base}{suffix}"
    return f"{base}{normalized_path}"


def auth_me_path() -> str:
    """Return the current-user endpoint path."""
    return f"{API_PREFIX}/auth/me"


def sync_article_path() -> str:
    """Return the article sync endpoint path."""
    return f"{API_PREFIX}/articles/sync"


def build_auth_headers(token: str, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
    """Build authenticated request headers."""
    headers = {"Authorization": f"Bearer {token}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


class NavClient:
    """Thin API client shared by local scripts."""

    def __init__(self, base_url: str, token: str, client: httpx.Client | None = None, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._owns_client = client is None

    def close(self) -> None:
        """Close the underlying HTTP client if owned."""
        if self._owns_client:
            self._client.close()

    def check_me(self) -> dict[str, Any]:
        """Validate the configured token."""
        response = self._request("GET", auth_me_path())
        return response.json()

    def sync_article(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sync an article payload."""
        response = self._request(
            "POST",
            sync_article_path(),
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def _request(self, method: str, path: str, headers: dict[str, str] | None = None, **kwargs) -> httpx.Response:
        response = self._client.request(
            method,
            build_api_url(self.base_url, path),
            headers=build_auth_headers(self.token, headers),
            **kwargs,
        )
        if response.status_code >= 400:
            detail = response.text.strip() or f"{response.status_code} {response.reason_phrase}"
            raise NavClientError(detail)
        return response
