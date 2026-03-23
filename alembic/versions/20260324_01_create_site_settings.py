"""create typed site settings table

Revision ID: 20260324_01
Revises:
Create Date: 2026-03-24 00:00:00
"""

from __future__ import annotations

import json
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from app.config import GITHUB_URL

# revision identifiers, used by Alembic.
revision = "20260324_01"
down_revision = "20260324_00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    site_settings_table = sa.Table(
        "site_settings",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("site_title", sa.String(length=255), nullable=False, server_default="个人主页导航"),
        sa.Column("article_page_title", sa.String(length=255), nullable=False, server_default="文章"),
        sa.Column("icp", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("copyright", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("link_size", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Shanghai"),
        sa.Column("github_url", sa.String(length=500), nullable=False, server_default=GITHUB_URL),
        sa.Column("analytics_code", sa.Text(), nullable=False, server_default=""),
        sa.Column("protected_article_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    metadata.create_all(bind=bind, checkfirst=True)

    inspector = inspect(bind)
    if "settings" not in inspector.get_table_names():
        return

    settings_table = sa.table(
        "settings",
        sa.column("key", sa.String()),
        sa.column("value", sa.Text()),
    )
    legacy_rows = bind.execute(sa.select(settings_table.c.key, settings_table.c.value)).all()
    legacy = {row.key: row.value for row in legacy_rows}
    if not legacy:
        return

    existing_row = bind.execute(
        sa.select(site_settings_table.c.id).limit(1)
    ).scalar_one_or_none()
    if existing_row is not None:
        raise RuntimeError(
            "Detected both populated 'site_settings' and legacy 'settings' tables. "
            "Refusing automatic migration because the source of truth is ambiguous. "
            "Back up the database, reconcile the duplicated settings data, and rerun "
            "'alembic upgrade head'."
        )

    protected_paths_raw = legacy.get("protected_article_paths", "[]")
    try:
        protected_paths = json.dumps(json.loads(protected_paths_raw), ensure_ascii=False)
    except (TypeError, json.JSONDecodeError):
        protected_paths = "[]"

    now = datetime.utcnow()
    bind.execute(
        sa.insert(site_settings_table).values(
            id=1,
            site_title=legacy.get("site_title") or "个人主页导航",
            article_page_title=legacy.get("article_page_title") or "文章",
            icp=legacy.get("icp") or "",
            copyright=legacy.get("copyright") or "",
            link_size=legacy.get("link_size") or "medium",
            timezone=legacy.get("timezone") or "Asia/Shanghai",
            github_url=legacy.get("github_url") or GITHUB_URL,
            analytics_code=legacy.get("analytics_code") or "",
            protected_article_paths_json=protected_paths,
            created_at=now,
            updated_at=now,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    sa.Table("site_settings", metadata).drop(bind=bind, checkfirst=True)
