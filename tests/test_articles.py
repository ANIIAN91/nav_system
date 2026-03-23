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
