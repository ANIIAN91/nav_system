"""Migration regression tests."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite+aiosqlite:///{db_path.resolve().as_posix()}"


def _run_alembic(db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": _sqlite_url(db_path),
            "SECRET_KEY": "migration-test-secret-key-32-chars-123456",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "admin123",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def test_alembic_upgrade_head_creates_core_schema_on_empty_db(tmp_path):
    db_path = tmp_path / "empty.db"

    result = _run_alembic(db_path, "upgrade", "head")

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    with _connect(db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {
            "alembic_version",
            "categories",
            "links",
            "site_settings",
            "token_blacklist",
            "update_logs",
            "visit_logs",
        }.issubset(table_names)
        assert "settings" not in table_names
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        assert version == ("20260324_03",)
        site_settings_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(site_settings)").fetchall()
        }
        assert "analytics_code" not in site_settings_columns


def test_alembic_upgrade_head_migrates_legacy_settings_table(tmp_path):
    db_path = tmp_path / "legacy.db"

    with _connect(db_path) as conn:
        conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            [
                ("site_title", "迁移后的站点"),
                ("article_page_title", "迁移后的文章页"),
                ("icp", "ICP 123456"),
                ("copyright", "Nav System"),
                ("link_size", "large"),
                ("timezone", "UTC"),
                ("github_url", "https://example.com/repo"),
                ("analytics_code", "<script>noop()</script>"),
                ("protected_article_paths", '["private/a.md","private/b.md"]'),
            ],
        )
        conn.commit()

    result = _run_alembic(db_path, "upgrade", "head")

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT site_title, article_page_title, icp, copyright, link_size, timezone,
                   github_url, protected_article_paths_json
            FROM site_settings
            WHERE id = 1
            """
        ).fetchone()
        assert row == (
            "迁移后的站点",
            "迁移后的文章页",
            "ICP 123456",
            "Nav System",
            "large",
            "UTC",
            "https://example.com/repo",
            '["private/a.md", "private/b.md"]',
        )
        site_settings_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(site_settings)").fetchall()
        }
        assert "analytics_code" not in site_settings_columns
        legacy_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
        ).fetchone()
        assert legacy_table is None


def test_alembic_upgrade_head_rejects_ambiguous_dual_settings_sources(tmp_path):
    db_path = tmp_path / "ambiguous.db"

    with _connect(db_path) as conn:
        conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("site_title", "legacy"))
        conn.execute(
            """
            CREATE TABLE site_settings (
                id INTEGER PRIMARY KEY,
                site_title TEXT NOT NULL
            )
            """
        )
        conn.execute("INSERT INTO site_settings (id, site_title) VALUES (?, ?)", (1, "typed"))
        conn.commit()

    result = _run_alembic(db_path, "upgrade", "head")
    combined_output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode != 0
    assert "Refusing automatic migration" in combined_output
