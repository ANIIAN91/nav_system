"""Settings API tests"""
import pytest

@pytest.mark.asyncio
async def test_get_settings(client):
    """Test getting settings"""
    response = await client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    # Check default values
    assert "site_title" in data
    assert "link_size" in data

@pytest.mark.asyncio
async def test_update_settings_unauthenticated(client):
    """Test updating settings without authentication fails"""
    response = await client.put(
        "/api/v1/settings",
        json={"site_title": "New Title"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_update_settings_authenticated(client, auth_headers):
    """Test updating settings with authentication"""
    response = await client.put(
        "/api/v1/settings",
        json={
            "site_title": "New Title",
            "link_size": "large",
            "icp": "",
            "copyright": "",
            "article_page_title": "文章",
            "protected_article_paths": [],
            "analytics_code": ""
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "设置已保存"
