"""Links API tests"""
import pytest
import pytest_asyncio

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
async def test_health_check(client):
    """Test health check endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
