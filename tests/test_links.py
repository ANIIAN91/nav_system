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
