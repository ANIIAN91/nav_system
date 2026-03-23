"""Article service tests."""

import pytest

from app.services.articles import ArticleAuthenticationRequiredError, ArticleService


def test_list_articles_filters_protected_paths(isolated_articles_dir):
    """Anonymous users should not see protected articles."""
    (isolated_articles_dir / "public").mkdir()
    (isolated_articles_dir / "private").mkdir()
    (isolated_articles_dir / "public" / "hello.md").write_text("# Hello", encoding="utf-8")
    (isolated_articles_dir / "private" / "secret.md").write_text("# Secret", encoding="utf-8")

    service = ArticleService()
    public_articles = service.list_articles(["private"], include_protected=False)
    all_articles = service.list_articles(["private"], include_protected=True)

    assert [article["path"] for article in public_articles] == ["public/hello.md"]
    assert sorted(article["path"] for article in all_articles) == ["private/secret.md", "public/hello.md"]


def test_get_article_blocks_protected_path_for_anonymous_user(isolated_articles_dir):
    """Protected paths should require authentication."""
    (isolated_articles_dir / "private").mkdir()
    (isolated_articles_dir / "private" / "secret.md").write_text("secret", encoding="utf-8")

    with pytest.raises(ArticleAuthenticationRequiredError):
        ArticleService().get_article("private/secret.md", ["private"], allow_protected=False)


def test_sync_article_rejects_path_escape(isolated_articles_dir):
    """Traversal attempts should be rejected."""
    with pytest.raises(ValueError):
        ArticleService().sync_article("../secret", "bad")


def test_sync_and_render_article_round_trip(isolated_articles_dir):
    """Synced article content should be readable and sanitized."""
    service = ArticleService()
    result = service.sync_article(
        "notes/hello",
        "# Hello\n\n<script>alert(1)</script>\n\nBody",
        frontmatter={"title": "Hello"},
    )
    article = service.get_article("notes/hello.md", [], allow_protected=True)

    assert result["path"] == "notes/hello.md"
    assert "---\ntitle: Hello\n---" in (isolated_articles_dir / "notes" / "hello.md").read_text(encoding="utf-8")
    assert "<script>" not in article["html"]
    assert "Body" in article["html"]


@pytest.mark.asyncio
async def test_article_async_facade_uses_threadpool(monkeypatch):
    """Async article facade should dispatch sync work through the threadpool helper."""
    service = ArticleService()
    captured = {}

    def fake_sync(path, protected_paths, allow_protected):
        captured["args"] = (path, protected_paths, allow_protected)
        return {"path": path}

    async def fake_run_in_threadpool(func, *args):
        captured["func"] = func
        return func(*args)

    monkeypatch.setattr(service, "get_article", fake_sync)
    monkeypatch.setattr("app.services.articles.run_in_threadpool", fake_run_in_threadpool)

    result = await service.get_article_async("notes/hello.md", ["private"], True)

    assert captured["func"] == fake_sync
    assert captured["args"] == ("notes/hello.md", ["private"], True)
    assert result == {"path": "notes/hello.md"}
