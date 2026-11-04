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
async def test_category_name_rejects_path_separators(client, auth_headers):
    """Category names should stay route-safe labels, not path-like values."""
    create_response = await client.post(
        "/api/v1/categories",
        json={"name": "Dev/Tools", "auth_required": False},
        headers=auth_headers,
    )
    assert create_response.status_code == 422

    await client.post(
        "/api/v1/categories",
        json={"name": "Dev", "auth_required": False},
        headers=auth_headers,
    )
    update_response = await client.put(
        "/api/v1/categories/Dev",
        json={"name": "Dev\\Tools", "auth_required": False},
        headers=auth_headers,
    )
    assert update_response.status_code == 422


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
    settings_response = await client.put(
        "/api/v1/settings",
        json={"private_mode": False},
        headers=auth_headers,
    )
    assert settings_response.status_code == 200

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


@pytest.mark.asyncio
async def test_private_mode_hides_all_categories_by_default(client, auth_headers):
    """Private mode is on by default, so anonymous visitors see no categories at all."""
    response = await client.post(
        "/api/v1/categories",
        json={"name": "Public Category", "auth_required": False},
        headers=auth_headers,
    )
    assert response.status_code == 200

    anonymous_list = await client.get("/api/v1/links")
    assert anonymous_list.status_code == 200
    assert anonymous_list.json()["categories"] == []

    authenticated_list = await client.get("/api/v1/links", headers=auth_headers)
    assert [c["name"] for c in authenticated_list.json()["categories"]] == ["Public Category"]


@pytest.mark.asyncio
async def test_new_categories_default_to_private(client, auth_headers):
    """Categories created without an explicit flag, or implicitly via add-link, require login."""
    explicit = await client.post("/api/v1/categories", json={"name": "No Flag"}, headers=auth_headers)
    assert explicit.status_code == 200
    assert explicit.json()["category"]["auth_required"] is True

    implicit = await client.post(
        "/api/v1/links?category_name=Implicit",
        json={"title": "Example", "url": "https://example.com"},
        headers=auth_headers,
    )
    assert implicit.status_code == 200

    listing = await client.get("/api/v1/links", headers=auth_headers)
    flags = {c["name"]: c["auth_required"] for c in listing.json()["categories"]}
    assert flags == {"No Flag": True, "Implicit": True}
