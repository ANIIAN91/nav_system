"""Shared URL validation helpers."""

from urllib.parse import urlparse

from app.utils.security import is_safe_url


def validate_url(
    url: str,
    *,
    allowed_schemes: tuple[str, ...],
    infer_https: bool = False,
) -> str:
    """Validate a user-provided URL and return the normalized value."""
    candidate = (url or "").strip()
    if not candidate or len(candidate) > 2048:
        raise ValueError("URL 长度无效")

    parsed = urlparse(candidate)
    if infer_https and not parsed.scheme:
        candidate = f"https://{candidate}"
        parsed = urlparse(candidate)

    if parsed.scheme not in allowed_schemes:
        allowed = "、".join(allowed_schemes)
        raise ValueError(f"URL 协议不支持，仅允许 {allowed}")

    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ValueError("URL 格式无效")

    return candidate


def validate_safe_external_url(url: str, *, infer_https: bool = False) -> str:
    """Validate a URL and ensure it does not target internal addresses."""
    candidate = validate_url(url, allowed_schemes=("http", "https"), infer_https=infer_https)
    safe, detail = is_safe_url(candidate)
    if not safe:
        raise ValueError(detail)
    return candidate
