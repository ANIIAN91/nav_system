"""Folder service."""

import shutil
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.core import normalize_article_path, safe_path_under_root


class FolderService:
    """File-backed folder operations."""

    def __init__(self, articles_dir: Path | None = None):
        self.articles_dir = articles_dir or get_settings().articles_dir

    def list_folders(self) -> list[dict]:
        """List top-level folders under the article root."""
        folders: list[dict] = []
        if not self.articles_dir.exists():
            return folders

        for item in sorted(self.articles_dir.iterdir(), key=lambda entry: entry.name.lower()):
            if not item.is_dir():
                continue
            folders.append(
                {
                    "name": item.name,
                    "path": item.name,
                    "article_count": len(list(item.rglob("*.md"))),
                }
            )
        return folders

    async def list_folders_async(self) -> list[dict]:
        """Run blocking folder listing off the event loop."""
        return await run_in_threadpool(self.list_folders)

    def create_folder(self, name: str) -> dict:
        """Create a folder relative to the article root."""
        normalized_name = normalize_article_path(name)
        if not normalized_name:
            raise ValueError("目录名称无效")

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
        normalized_name = normalize_article_path(name)
        normalized_new_name = normalize_article_path(new_name)
        if not normalized_new_name:
            raise ValueError("新目录名称无效")

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
        normalized_name = normalize_article_path(name)
        folder_path = safe_path_under_root(self.articles_dir, normalized_name)
        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError("目录不存在")

        article_count = len(list(folder_path.rglob("*.md")))
        shutil.rmtree(folder_path)
        return {"name": normalized_name, "article_count": article_count}

    async def delete_folder_async(self, name: str) -> dict:
        """Run blocking folder deletion off the event loop."""
        return await run_in_threadpool(self.delete_folder, name)
