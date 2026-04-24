"""Folder service."""

import shutil
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.core import normalize_article_path, safe_path_under_root


def _normalize_folder_name(name: str, message: str = "目录名称无效") -> str:
    normalized_name = normalize_article_path(name)
    if not normalized_name:
        raise ValueError(message)
    return normalized_name


class FolderService:
    """File-backed folder operations."""

    def __init__(self, articles_dir: Path | None = None):
        self.articles_dir = articles_dir or get_settings().articles_dir

    def list_folders(self) -> list[dict]:
        """List folders under the article root, including nested directories."""
        folders: list[dict] = []
        if not self.articles_dir.exists():
            return folders

        for item in sorted(
            (path for path in self.articles_dir.rglob("*") if path.is_dir()),
            key=lambda entry: entry.relative_to(self.articles_dir).as_posix().lower(),
        ):
            relative_path = item.relative_to(self.articles_dir).as_posix()
            if not relative_path or relative_path == ".":
                continue
            folders.append(
                {
                    "name": relative_path,
                    "path": relative_path,
                    "article_count": len(list(item.rglob("*.md"))),
                }
            )
        return folders

    async def list_folders_async(self) -> list[dict]:
        """Run blocking folder listing off the event loop."""
        return await run_in_threadpool(self.list_folders)

    def create_folder(self, name: str) -> dict:
        """Create a folder relative to the article root."""
        normalized_name = _normalize_folder_name(name)

        folder_path = safe_path_under_root(self.articles_dir, normalized_name)
        if folder_path.exists():
            raise FileExistsError("目录已存在")

        folder_path.mkdir(parents=True, exist_ok=False)
        return {"name": normalized_name, "path": normalized_name, "article_count": 0}

    async def create_folder_async(self, name: str) -> dict:
        """Run blocking folder creation off the event loop."""
        return await run_in_threadpool(self.create_folder, name)

    def rename_folder(self, name: str, new_name: str) -> dict:
        """Rename an existing folder."""
        normalized_name = _normalize_folder_name(name)
        normalized_new_name = _normalize_folder_name(new_name, "新目录名称无效")

        folder_path = safe_path_under_root(self.articles_dir, normalized_name)
        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError("目录不存在")

        new_path = safe_path_under_root(self.articles_dir, normalized_new_name)
        if new_path.exists():
            raise FileExistsError("目标目录已存在")

        folder_path.rename(new_path)
        return {"old_name": normalized_name, "new_name": normalized_new_name}

    async def rename_folder_async(self, name: str, new_name: str) -> dict:
        """Run blocking folder renames off the event loop."""
        return await run_in_threadpool(self.rename_folder, name, new_name)

    def delete_folder(self, name: str) -> dict:
        """Delete a folder and count contained articles."""
        normalized_name = _normalize_folder_name(name)
        folder_path = safe_path_under_root(self.articles_dir, normalized_name)
        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError("目录不存在")

        article_count = len(list(folder_path.rglob("*.md")))
        shutil.rmtree(folder_path)
        return {"name": normalized_name, "article_count": article_count}

    async def delete_folder_async(self, name: str) -> dict:
        """Run blocking folder deletion off the event loop."""
        return await run_in_threadpool(self.delete_folder, name)
