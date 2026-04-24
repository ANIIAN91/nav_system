"""Folder service tests."""

import pytest

from app.services.folders import FolderService


def test_folder_service_crud(isolated_articles_dir):
    """Folder service should create, rename, and delete directories."""
    service = FolderService()

    created = service.create_folder("notes")
    assert created["name"] == "notes"
    assert (isolated_articles_dir / "notes").exists()

    renamed = service.rename_folder("notes", "archive")
    assert renamed == {"old_name": "notes", "new_name": "archive"}
    assert not (isolated_articles_dir / "notes").exists()
    assert (isolated_articles_dir / "archive").exists()

    deleted = service.delete_folder("archive")
    assert deleted["name"] == "archive"
    assert not (isolated_articles_dir / "archive").exists()


def test_folder_service_lists_nested_directories(isolated_articles_dir):
    """Nested folders should be visible in the management list."""
    service = FolderService()

    service.create_folder("notes")
    service.create_folder("notes/weekly")
    (isolated_articles_dir / "notes" / "weekly" / "hello.md").write_text("# Hello", encoding="utf-8")

    folders = service.list_folders()

    assert folders == [
        {"name": "notes", "path": "notes", "article_count": 1},
        {"name": "notes/weekly", "path": "notes/weekly", "article_count": 1},
    ]


def test_folder_service_rejects_escape(isolated_articles_dir):
    """Folder traversal should be rejected."""
    with pytest.raises(ValueError):
        FolderService().create_folder("../secret")


def test_folder_service_rejects_root_folder_operations(isolated_articles_dir):
    """Root folder aliases should not operate on the whole article directory."""
    service = FolderService()
    (isolated_articles_dir / "hello.md").write_text("# Hello", encoding="utf-8")

    with pytest.raises(ValueError):
        service.rename_folder(".", "archive")
    with pytest.raises(ValueError):
        service.delete_folder(".")

    assert isolated_articles_dir.exists()
    assert (isolated_articles_dir / "hello.md").exists()


@pytest.mark.asyncio
async def test_folder_async_facade_uses_threadpool(monkeypatch):
    """Async folder facade should dispatch sync work through the threadpool helper."""
    service = FolderService()
    captured = {}

    def fake_sync():
        captured["called"] = True
        return [{"name": "notes"}]

    async def fake_run_in_threadpool(func, *args):
        captured["func"] = func
        return func(*args)

    monkeypatch.setattr(service, "list_folders", fake_sync)
    monkeypatch.setattr("app.services.folders.run_in_threadpool", fake_run_in_threadpool)

    result = await service.list_folders_async()

    assert captured["func"] == fake_sync
    assert captured["called"] is True
    assert result == [{"name": "notes"}]
