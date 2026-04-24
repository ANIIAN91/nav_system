"""Settings API tests."""

import pytest


@pytest.mark.asyncio
async def test_get_settings(client):
    """Test getting settings."""
    response = await client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert "site_title" in data
    assert "link_size" in data
    assert "version" in data
    assert "protected_article_paths" not in data


@pytest.mark.asyncio
async def test_get_admin_settings_requires_auth(client):
    """Full settings should not be publicly readable."""
    response = await client.get("/api/v1/settings/admin")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_settings_unauthenticated(client):
    """Test updating settings without authentication fails."""
    response = await client.put(
        "/api/v1/settings",
        json={"site_title": "New Title"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_settings_authenticated(client, auth_headers):
    """Test updating settings with authentication."""
    response = await client.put(
        "/api/v1/settings",
        json={
            "site_title": "New Title",
            "link_size": "large",
            "icp": "ICP-TEST",
            "copyright": "2026",
            "article_page_title": "文章页",
            "protected_article_paths": ["private", "notes\\secret"],
            "github_url": "https://example.com/repo",
            "timezone": "Asia/Tokyo",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "设置已保存"
    assert data["settings"]["site_title"] == "New Title"
    assert data["settings"]["link_size"] == "large"
    assert data["settings"]["protected_article_paths"] == ["private", "notes/secret"]
    assert data["settings"]["github_url"] == "https://example.com/repo"
    assert data["settings"]["version"]
    assert "analytics_code" not in data["settings"]

    get_response = await client.get("/api/v1/settings")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["site_title"] == "New Title"
    assert get_data["timezone"] == "Asia/Tokyo"
    assert "protected_article_paths" not in get_data
    assert "analytics_code" not in get_data

    admin_response = await client.get("/api/v1/settings/admin", headers=auth_headers)
    assert admin_response.status_code == 200
    admin_data = admin_response.json()
    assert admin_data["protected_article_paths"] == ["private", "notes/secret"]
    assert admin_data["timezone"] == "Asia/Tokyo"


@pytest.mark.asyncio
async def test_update_settings_rejects_unknown_fields(client, auth_headers):
    """Unknown payload fields should be rejected by the typed settings contract."""
    response = await client.put(
        "/api/v1/settings",
        json={"site_title": "New Title", "analytics_code": "<script>noop()</script>"},
        headers=auth_headers,
    )
    assert response.status_code == 422
