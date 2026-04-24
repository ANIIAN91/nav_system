"""Articles API tests"""
import pytest


@pytest.mark.asyncio
async def test_sync_article_and_fetch(client, auth_headers, isolated_articles_dir):
    """Test syncing an article creates a file and returns it via API"""
    response = await client.post(
        "/api/v1/articles/sync",
        json={
            "path": "notes/hello",
            "content": "# Hello\n\nBody text"
        },
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["path"] == "notes/hello.md"
    assert (isolated_articles_dir / "notes" / "hello.md").exists()

    list_response = await client.get("/api/v1/articles")
    assert list_response.status_code == 200
    articles = list_response.json()["articles"]
    assert any(article["path"] == "notes/hello.md" for article in articles)

    get_response = await client.get("/api/v1/articles/notes/hello.md")
    assert get_response.status_code == 200
    article = get_response.json()
    assert article["path"] == "notes/hello.md"
    assert "# Hello" in article["content"]
    assert "Body text" in article["html"]


@pytest.mark.asyncio
async def test_legacy_article_routes_redirect_to_home(client, auth_headers, isolated_articles_dir):
    response = await client.post(
        "/api/v1/articles/sync",
        json={"path": "notes/legacy", "content": "# Legacy"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    list_page = await client.get("/articles", follow_redirects=False)
    detail_page = await client.get("/articles/notes/legacy.md", follow_redirects=False)

    assert list_page.status_code == 307
    assert list_page.headers["location"] == "/"
    assert detail_page.status_code == 307
    assert detail_page.headers["location"] == "/?article=notes%2Flegacy.md"
