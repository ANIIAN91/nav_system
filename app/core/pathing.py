"""Shared helpers for safe article and folder path handling."""

from pathlib import Path, PurePosixPath
from typing import Iterable


def ensure_posix_path(path: str | Path) -> str:
    """Normalize separators to POSIX style without changing path meaning."""
    return str(path).replace("\\", "/")


def normalize_article_path(path: str | Path) -> str:
    """Normalize a relative article path and reject traversal segments."""
    raw_path = ensure_posix_path(path).strip().lstrip("/")
    if raw_path in {"", "."}:
        return ""

    normalized = PurePosixPath(raw_path).as_posix()
    parts = []
    for part in PurePosixPath(normalized).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError("路径不能包含上级目录跳转")
        parts.append(part)
    return "/".join(parts)


def safe_path_under_root(root: Path, relative_path: str | Path) -> Path:
    """Resolve a relative path under root and reject escapes."""
    root_path = Path(root).resolve()
    normalized = normalize_article_path(relative_path)
    resolved = (root_path / normalized).resolve()
    if resolved != root_path and root_path not in resolved.parents:
        raise ValueError("路径超出允许范围")
    return resolved


def is_path_protected(path: str | Path, protected_paths: Iterable[str]) -> bool:
    """Return True when path is inside one of the protected prefixes."""
    normalized_path = normalize_article_path(path)
    if not normalized_path:
        return False

    path_parts = PurePosixPath(normalized_path).parts
    for protected_path in protected_paths:
        normalized_protected = normalize_article_path(protected_path)
        if not normalized_protected:
            continue
        protected_parts = PurePosixPath(normalized_protected).parts
        if len(path_parts) >= len(protected_parts) and path_parts[: len(protected_parts)] == protected_parts:
            return True
    return False
