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


@pytest.mark.asyncio
async def test_batch_reorder_categories(client, auth_headers):
    """Batch reorder should persist the provided category order."""
    for name in ("Alpha", "Beta", "Gamma"):
        response = await client.post(
            "/api/v1/categories",
            json={"name": name, "auth_required": False},
            headers=auth_headers,
        )
        assert response.status_code == 200

    reorder_response = await client.post(
        "/api/v1/categories/reorder/batch",
        json={"ids": ["Gamma", "Alpha", "Beta"]},
        headers=auth_headers,
    )
    assert reorder_response.status_code == 200
    assert reorder_response.json()["message"] == "排序成功"

    list_response = await client.get("/api/v1/links", headers=auth_headers)
    assert list_response.status_code == 200
    category_names = [category["name"] for category in list_response.json()["categories"]]
    assert category_names == ["Gamma", "Alpha", "Beta"]


@pytest.mark.asyncio
async def test_batch_reorder_categories_rejects_partial_payload(client, auth_headers):
    """Batch reorder should fail when not all categories are present."""
    for name in ("Alpha", "Beta", "Gamma"):
        response = await client.post(
            "/api/v1/categories",
            json={"name": name, "auth_required": False},
            headers=auth_headers,
        )
        assert response.status_code == 200

    reorder_response = await client.post(
        "/api/v1/categories/reorder/batch",
        json={"ids": ["Gamma", "Alpha"]},
        headers=auth_headers,
    )

    assert reorder_response.status_code == 400


@pytest.mark.asyncio
async def test_category_visibility_depends_on_authentication(client, auth_headers):
    """Private categories should be hidden from unauthenticated responses."""
    public_response = await client.post(
        "/api/v1/categories",
        json={"name": "Public Category", "auth_required": False},
        headers=auth_headers,
    )
    assert public_response.status_code == 200

    private_response = await client.post(
        "/api/v1/categories",
        json={"name": "Private Category", "auth_required": True},
        headers=auth_headers,
    )
    assert private_response.status_code == 200

    anonymous_list = await client.get("/api/v1/links")
    assert anonymous_list.status_code == 200
    anonymous_names = [category["name"] for category in anonymous_list.json()["categories"]]
    assert "Public Category" in anonymous_names
    assert "Private Category" not in anonymous_names

    authenticated_list = await client.get("/api/v1/links", headers=auth_headers)
    assert authenticated_list.status_code == 200
    authenticated_names = [category["name"] for category in authenticated_list.json()["categories"]]
    assert "Public Category" in authenticated_names
    assert "Private Category" in authenticated_names
