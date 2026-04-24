"""Endpoint contract tests."""

from pathlib import Path

from scripts.nav_client import auth_me_path, build_api_url, sync_article_path


def test_nav_client_endpoint_builders():
    """Python endpoint builders should preserve the /api/v1 contract."""
    assert auth_me_path() == "/api/v1/auth/me"
    assert sync_article_path() == "/api/v1/articles/sync"
    assert build_api_url("http://localhost:8001", sync_article_path()) == "http://localhost:8001/api/v1/articles/sync"
    assert build_api_url("http://localhost:8001/api/v1", auth_me_path()) == "http://localhost:8001/api/v1/auth/me"


def test_sync_script_uses_shared_nav_client():
    """Sync script should delegate endpoint assembly to nav_client."""
    content = Path("scripts/sync_articles.py").read_text(encoding="utf-8")
    assert "from scripts.nav_client import NavClient" in content or "from nav_client import NavClient" in content
    assert '"/api/v1/articles/sync"' not in content
    assert '"/api/v1/auth/me"' not in content


def test_obsidian_plugin_uses_shared_api_module():
    """Plugin main module should stop hardcoding API endpoints."""
    main_js = Path("obsidian-plugin/main.js").read_text(encoding="utf-8")
    api_js = Path("obsidian-plugin/api.js").read_text(encoding="utf-8")

    assert "require('./api')" in main_js
    assert "/api/v1/articles/sync" not in main_js
    assert "/api/v1/auth/me" not in main_js
    assert "const API_PREFIX = \"/api/v1\";" in api_js


def test_home_page_uses_module_entry_and_shared_endpoints():
    """Browser home page should use the module entry and shared endpoint builders."""
    index_template = Path("templates/index.html").read_text(encoding="utf-8")
    home_js = Path("static/js/pages/home.js").read_text(encoding="utf-8")

    assert 'type="module" src="/static/js/pages/home.js"' in index_template
    assert "/static/js/main.js" not in index_template
    assert 'from "../core/endpoints.js"' in home_js
    assert "/api/v1/" not in home_js
    assert not Path("static/js/main.js").exists()
    assert Path("static/js/pages/home/article-sheet.js").exists()
    assert Path("static/js/pages/home/article-manager.js").exists()

def test_legacy_article_page_bundle_removed():
    """Legacy dedicated article page frontend should stay removed."""
    assert not Path("templates/article.html").exists()
    assert not Path("static/js/pages/articles.js").exists()


def test_home_page_logout_uses_revoke_flow():
    """Browser logout should continue to call the shared revoke flow."""
    home_js = Path("static/js/pages/home.js").read_text(encoding="utf-8")
    auth_js = Path("static/js/core/auth.js").read_text(encoding="utf-8")

    assert 'revokeSession' in home_js
    assert 'await revokeSession(token);' in home_js
    assert 'endpoints.auth.logout()' in auth_js


def test_legacy_settings_compatibility_layer_removed():
    """Legacy settings model/schema files should stay deleted after cutover."""
    settings_service = Path("app/services/settings.py").read_text(encoding="utf-8")
    drop_migration = Path("alembic/versions/20260324_02_drop_legacy_settings_table.py").read_text(
        encoding="utf-8"
    )

    assert not Path("app/models/setting.py").exists()
    assert not Path("app/schemas/setting.py").exists()
    assert "_load_legacy_settings" not in settings_service
    assert "_sync_legacy_settings" not in settings_service
    assert 'op.drop_table("settings")' in drop_migration
