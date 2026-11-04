"""Links API tests"""
import pytest

@pytest.mark.asyncio
async def test_get_links_unauthenticated(client):
    """Test getting links without authentication"""
    response = await client.get("/api/v1/links")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data

@pytest.mark.asyncio
async def test_add_link_unauthenticated(client):
    """Test adding link without authentication fails"""
    response = await client.post(
        "/api/v1/links?category_name=Test",
        json={"title": "Test", "url": "https://test.com"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_add_link_authenticated(client, auth_headers):
    """Test adding link with authentication"""
    response = await client.post(
        "/api/v1/links?category_name=Test",
        json={"title": "Test Link", "url": "https://test.com"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "添加成功"
    assert data["link"]["title"] == "Test Link"


@pytest.mark.asyncio
async def test_add_link_rejects_path_like_category_name(client, auth_headers):
    """Adding a link must not auto-create categories that cannot be addressed later."""
    response = await client.post(
        "/api/v1/links?category_name=Dev%2FTools",
        json={"title": "Test Link", "url": "https://test.com"},
        headers=auth_headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_batch_reorder_links(client, auth_headers):
    """Batch reorder should persist the provided link order within a category."""
    created_links = []
    for title in ("Alpha", "Beta", "Gamma"):
        response = await client.post(
            "/api/v1/links?category_name=Reorder",
            json={"title": title, "url": f"https://{title.lower()}.example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        created_links.append(response.json()["link"])

    reorder_response = await client.post(
        "/api/v1/links/reorder/batch",
        json={"ids": [created_links[2]["id"], created_links[0]["id"], created_links[1]["id"]]},
        headers=auth_headers,
    )
    assert reorder_response.status_code == 200
    assert reorder_response.json()["message"] == "排序成功"

    list_response = await client.get("/api/v1/links", headers=auth_headers)
    assert list_response.status_code == 200
    categories = list_response.json()["categories"]
    reorder_category = next(category for category in categories if category["name"] == "Reorder")
    assert [link["title"] for link in reorder_category["links"]] == ["Gamma", "Alpha", "Beta"]


@pytest.mark.asyncio
async def test_batch_reorder_links_rejects_partial_category_payload(client, auth_headers):
    """Batch reorder should fail when the payload omits links from the same category."""
    created_links = []
    for title in ("Alpha", "Beta", "Gamma"):
        response = await client.post(
            "/api/v1/links?category_name=Partial",
            json={"title": title, "url": f"https://{title.lower()}.example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        created_links.append(response.json()["link"])

    reorder_response = await client.post(
        "/api/v1/links/reorder/batch",
        json={"ids": [created_links[0]["id"], created_links[1]["id"]]},
        headers=auth_headers,
    )

    assert reorder_response.status_code == 400


@pytest.mark.asyncio
async def test_batch_reorder_links_rejects_cross_category_payload(client, auth_headers):
    """Batch reorder should fail when links from different categories are mixed."""
    alpha = await client.post(
        "/api/v1/links?category_name=CatA",
        json={"title": "Alpha", "url": "https://alpha.example.com"},
        headers=auth_headers,
    )
    beta = await client.post(
        "/api/v1/links?category_name=CatA",
        json={"title": "Beta", "url": "https://beta.example.com"},
        headers=auth_headers,
    )
    gamma = await client.post(
        "/api/v1/links?category_name=CatB",
        json={"title": "Gamma", "url": "https://gamma.example.com"},
        headers=auth_headers,
    )
    assert alpha.status_code == beta.status_code == gamma.status_code == 200

    reorder_response = await client.post(
        "/api/v1/links/reorder/batch",
        json={
            "ids": [
                alpha.json()["link"]["id"],
                beta.json()["link"]["id"],
                gamma.json()["link"]["id"],
            ]
        },
        headers=auth_headers,
    )

    assert reorder_response.status_code == 400


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_add_link_without_title_uses_fetched_metadata(client, auth_headers, monkeypatch):
    """Quick add should fill title and icon from the fetched page."""

    async def fake_fetch_favicon(url):
        return {"icon": "hashed.png", "title": "Example Domain", "message": "ok"}

    monkeypatch.setattr("app.application.use_cases.navigation.fetch_favicon", fake_fetch_favicon)
    monkeypatch.setattr("app.application.use_cases.navigation.validate_safe_external_url", lambda url: url)

    response = await client.post(
        "/api/v1/links?category_name=Quick",
        json={"url": "https://example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    link = response.json()["link"]
    assert link["title"] == "Example Domain"
    assert link["icon"] == "hashed.png"


@pytest.mark.asyncio
async def test_add_link_without_title_falls_back_to_hostname(client, auth_headers, monkeypatch):
    """When the page title cannot be fetched, the hostname becomes the title."""

    async def fake_fetch_favicon(url):
        return {"icon": None, "title": None, "message": "failed"}

    monkeypatch.setattr("app.application.use_cases.navigation.fetch_favicon", fake_fetch_favicon)
    monkeypatch.setattr("app.application.use_cases.navigation.validate_safe_external_url", lambda url: url)

    response = await client.post(
        "/api/v1/links?category_name=Quick",
        json={"url": "https://docs.example.com/path", "title": "  "},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["link"]["title"] == "docs.example.com"


@pytest.mark.asyncio
async def test_add_link_with_title_fetches_icon_only_when_requested(client, auth_headers, monkeypatch):
    """Bookmarklet adds keep the given title but still fetch the icon; plain adds do not fetch."""
    calls = []

    async def fake_fetch_favicon(url):
        calls.append(url)
        return {"icon": "hashed.png", "title": "Fetched Title", "message": "ok"}

    monkeypatch.setattr("app.application.use_cases.navigation.fetch_favicon", fake_fetch_favicon)
    monkeypatch.setattr("app.application.use_cases.navigation.validate_safe_external_url", lambda url: url)

    response = await client.post(
        "/api/v1/links?category_name=Quick",
        json={"url": "https://example.com", "title": "My Title", "fetch_icon": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["link"]["title"] == "My Title"
    assert response.json()["link"]["icon"] == "hashed.png"

    plain = await client.post(
        "/api/v1/links?category_name=Quick",
        json={"url": "https://example.org", "title": "Plain"},
        headers=auth_headers,
    )
    assert plain.status_code == 200
    assert calls == ["https://example.com"]


@pytest.mark.asyncio
async def test_native_import_skips_duplicate_urls(client, auth_headers):
    """Re-importing the same bookmarks should not create duplicate links."""
    payload = {
        "format": "native",
        "data": {
            "categories": [
                {
                    "name": "Bookmarks",
                    "links": [
                        {"title": "A", "url": "https://a.example.com"},
                        {"title": "A again", "url": "https://a.example.com"},
                        {"title": "B", "url": "https://b.example.com"},
                        {"title": "Bad", "url": "javascript:alert(1)"},
                    ],
                }
            ]
        },
    }
    first = await client.post("/api/v1/links/import", json=payload, headers=auth_headers)
    assert first.status_code == 200
    assert "新增 2 个" in first.json()["message"]

    second = await client.post("/api/v1/links/import", json=payload, headers=auth_headers)
    assert second.status_code == 200
    assert "新增 0 个" in second.json()["message"]

    listing = await client.get("/api/v1/links", headers=auth_headers)
    bookmarks = next(c for c in listing.json()["categories"] if c["name"] == "Bookmarks")
    assert [link["url"] for link in bookmarks["links"]] == ["https://a.example.com", "https://b.example.com"]
    assert bookmarks["auth_required"] is True
