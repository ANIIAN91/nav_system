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


def test_folder_service_rejects_escape(isolated_articles_dir):
    """Folder traversal should be rejected."""
    with pytest.raises(ValueError):
        FolderService().create_folder("../secret")


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
