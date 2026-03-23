"""Article service."""

from pathlib import Path
from typing import Iterable

import bleach
import markdown
import yaml
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.core import is_path_protected, normalize_article_path, safe_path_under_root

MARKDOWN_EXTENSIONS = [
    "fenced_code",
    "tables",
    "toc",
    "codehilite",
    "nl2br",
    "sane_lists",
]
ALLOWED_TAGS = [
    "p",
    "a",
    "strong",
    "em",
    "ul",
    "ol",
    "li",
    "code",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "hr",
    "br",
    "img",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "div",
    "span",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt"],
    "code": ["class"],
    "pre": ["class"],
    "div": ["class"],
    "span": ["class"],
}


class ArticleAuthenticationRequiredError(PermissionError):
    """Raised when an anonymous user requests a protected article."""


class ArticleService:
    """File-backed article operations."""

    def __init__(self, articles_dir: Path | None = None):
        self.articles_dir = articles_dir or get_settings().articles_dir

    def list_articles(self, protected_paths: Iterable[str], include_protected: bool) -> list[dict]:
        """List articles visible to the current caller."""
        articles: list[dict] = []
        if not self.articles_dir.exists():
            return articles

        for path in self.articles_dir.rglob("*.md"):
            rel_path = path.relative_to(self.articles_dir)
            rel_path_str = rel_path.as_posix()
            protected = is_path_protected(rel_path_str, protected_paths)
            if protected and not include_protected:
                continue

            stat = path.stat()
            category = rel_path.parent.as_posix() if rel_path.parent != Path(".") else None
            articles.append(
                {
                    "path": rel_path_str,
                    "title": path.stem,
                    "category": category,
                    "protected": protected,
                    "created_time": stat.st_mtime,
                }
            )

        articles.sort(key=lambda item: item["created_time"], reverse=True)
        return articles

    async def list_articles_async(self, protected_paths: Iterable[str], include_protected: bool) -> list[dict]:
        """Run blocking article listing off the event loop."""
        return await run_in_threadpool(self.list_articles, protected_paths, include_protected)

    def get_article(self, path: str, protected_paths: Iterable[str], allow_protected: bool) -> dict:
        """Read article content and rendered HTML."""
        normalized_path = normalize_article_path(path)
        if is_path_protected(normalized_path, protected_paths) and not allow_protected:
            raise ArticleAuthenticationRequiredError("需要登录才能查看此文章")

        article_path = safe_path_under_root(self.articles_dir, normalized_path)
        if not article_path.exists() or not article_path.is_file() or article_path.suffix.lower() != ".md":
            raise FileNotFoundError("文章不存在")

        content = article_path.read_text(encoding="utf-8")
        return {
            "path": normalized_path,
            "content": content,
            "html": self.render_markdown(content),
        }

    async def get_article_async(
        self,
        path: str,
        protected_paths: Iterable[str],
        allow_protected: bool,
    ) -> dict:
        """Run blocking article reads and markdown rendering off the event loop."""
        return await run_in_threadpool(self.get_article, path, protected_paths, allow_protected)

    def sync_article(self, path: str, content: str, title: str | None = None, frontmatter: dict | None = None) -> dict:
        """Write article content, optionally prepending frontmatter."""
        normalized_path = normalize_article_path(path)
        if not normalized_path:
            raise ValueError("文章路径不能为空")
        if not normalized_path.endswith(".md"):
            normalized_path = f"{normalized_path}.md"

        article_path = safe_path_under_root(self.articles_dir, normalized_path)
        article_path.parent.mkdir(parents=True, exist_ok=True)

        final_content = content
        if frontmatter:
            frontmatter_str = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
            final_content = f"---\n{frontmatter_str}---\n\n{content}"

        article_path.write_text(final_content, encoding="utf-8")
        return {
            "message": "文章同步成功",
            "path": normalized_path,
            "title": title or article_path.stem,
        }

    async def sync_article_async(
        self,
        path: str,
        content: str,
        title: str | None = None,
        frontmatter: dict | None = None,
    ) -> dict:
        """Run blocking article writes off the event loop."""
        return await run_in_threadpool(
            self.sync_article,
            path,
            content,
            title,
            frontmatter,
        )

    def update_article(self, path: str, content: str) -> dict:
        """Overwrite an existing article."""
        normalized_path = normalize_article_path(path)
        article_path = safe_path_under_root(self.articles_dir, normalized_path)
        if not article_path.exists() or not article_path.is_file() or article_path.suffix.lower() != ".md":
            raise FileNotFoundError("文章不存在")

        article_path.write_text(content, encoding="utf-8")
        return {"path": normalized_path, "title": article_path.stem}

    async def update_article_async(self, path: str, content: str) -> dict:
        """Run blocking article updates off the event loop."""
        return await run_in_threadpool(self.update_article, path, content)

    def delete_article(self, path: str) -> dict:
        """Delete an existing article."""
        normalized_path = normalize_article_path(path)
        article_path = safe_path_under_root(self.articles_dir, normalized_path)
        if not article_path.exists() or not article_path.is_file():
            raise FileNotFoundError("文章不存在")

        title = article_path.stem
        article_path.unlink()
        return {"path": normalized_path, "title": title}

    async def delete_article_async(self, path: str) -> dict:
        """Run blocking article deletion off the event loop."""
        return await run_in_threadpool(self.delete_article, path)

    @staticmethod
    def render_markdown(content: str) -> str:
        """Render markdown and sanitize HTML output."""
        html_content = markdown.markdown(content, extensions=MARKDOWN_EXTENSIONS)
        return bleach.clean(
            html_content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True,
        )
