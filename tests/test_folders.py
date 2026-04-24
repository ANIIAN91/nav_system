"""Folders API tests"""
import pytest


@pytest.mark.asyncio
async def test_folder_crud(client, auth_headers, isolated_articles_dir):
    """Test creating, renaming and deleting folders"""
    create_response = await client.post(
        "/api/v1/folders?name=notes",
        headers=auth_headers
    )
    assert create_response.status_code == 200
    assert (isolated_articles_dir / "notes").exists()

    list_response = await client.get("/api/v1/folders", headers=auth_headers)
    assert list_response.status_code == 200
    folders = list_response.json()["folders"]
    assert any(folder["name"] == "notes" for folder in folders)

    rename_response = await client.put(
        "/api/v1/folders/notes",
        json={"new_name": "archive"},
        headers=auth_headers
    )
    assert rename_response.status_code == 200
    assert not (isolated_articles_dir / "notes").exists()
    assert (isolated_articles_dir / "archive").exists()

    delete_response = await client.delete(
        "/api/v1/folders/archive",
        headers=auth_headers
    )
    assert delete_response.status_code == 200
    assert not (isolated_articles_dir / "archive").exists()


@pytest.mark.asyncio
async def test_folder_list_includes_nested_directories(client, auth_headers, isolated_articles_dir):
    """Nested folders should be returned so the homepage manager can operate on them."""
    nested = isolated_articles_dir / "notes" / "weekly"
    nested.mkdir(parents=True)
    (nested / "hello.md").write_text("# Hello", encoding="utf-8")

    response = await client.get("/api/v1/folders", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["folders"] == [
        {"name": "notes", "path": "notes", "article_count": 1},
        {"name": "notes/weekly", "path": "notes/weekly", "article_count": 1},
    ]


@pytest.mark.asyncio
async def test_folder_api_rejects_root_delete(client, auth_headers, isolated_articles_dir):
    """Deleting a root folder alias should not delete the article root."""
    (isolated_articles_dir / "hello.md").write_text("# Hello", encoding="utf-8")

    response = await client.delete("/api/v1/folders/.", headers=auth_headers)

    assert response.status_code != 200
    assert isolated_articles_dir.exists()
    assert (isolated_articles_dir / "hello.md").exists()
