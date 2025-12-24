"""Categories API tests"""
import pytest

@pytest.mark.asyncio
async def test_add_category_unauthenticated(client):
    """Test adding category without authentication fails"""
    response = await client.post(
        "/api/v1/categories",
        json={"name": "Test Category", "auth_required": False}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_add_category_authenticated(client, auth_headers):
    """Test adding category with authentication"""
    response = await client.post(
        "/api/v1/categories",
        json={"name": "Test Category", "auth_required": False},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "添加成功"
    assert data["category"]["name"] == "Test Category"

@pytest.mark.asyncio
async def test_add_duplicate_category(client, auth_headers):
    """Test adding duplicate category fails"""
    # Add first category
    await client.post(
        "/api/v1/categories",
        json={"name": "Duplicate", "auth_required": False},
        headers=auth_headers
    )
    # Try to add duplicate
    response = await client.post(
        "/api/v1/categories",
        json={"name": "Duplicate", "auth_required": False},
        headers=auth_headers
    )
    assert response.status_code == 400
