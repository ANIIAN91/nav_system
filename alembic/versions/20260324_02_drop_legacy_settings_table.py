"""drop legacy settings table

Revision ID: 20260324_02
Revises: 20260324_01
Create Date: 2026-03-24 00:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260324_02"
down_revision = "20260324_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop the legacy key-value settings table after full cutover."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "settings" not in table_names:
        return
    if "site_settings" not in table_names:
        raise RuntimeError(
            "Refusing to drop legacy 'settings' because 'site_settings' is missing. "
            "Run the preceding migrations or restore from backup before retrying."
        )

    settings_count = bind.execute(sa.text("SELECT COUNT(*) FROM settings")).scalar_one()
    site_settings_count = bind.execute(sa.text("SELECT COUNT(*) FROM site_settings")).scalar_one()
    if settings_count and not site_settings_count:
        raise RuntimeError(
            "Refusing to drop legacy 'settings' because it still contains data while "
            "'site_settings' has no rows."
        )

    op.drop_table("settings")


def downgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.current_timestamp(),
        ),
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "site_settings" not in inspector.get_table_names():
        return

    site_settings_table = sa.table(
        "site_settings",
        sa.column("id", sa.Integer()),
        sa.column("site_title", sa.String()),
        sa.column("article_page_title", sa.String()),
        sa.column("icp", sa.String()),
        sa.column("copyright", sa.String()),
        sa.column("link_size", sa.String()),
        sa.column("timezone", sa.String()),
        sa.column("github_url", sa.String()),
        sa.column("analytics_code", sa.Text()),
        sa.column("protected_article_paths_json", sa.Text()),
    )
    row = bind.execute(
        sa.select(
            site_settings_table.c.site_title,
            site_settings_table.c.article_page_title,
            site_settings_table.c.icp,
            site_settings_table.c.copyright,
            site_settings_table.c.link_size,
            site_settings_table.c.timezone,
            site_settings_table.c.github_url,
            site_settings_table.c.analytics_code,
            site_settings_table.c.protected_article_paths_json,
        ).where(site_settings_table.c.id == 1)
    ).mappings().first()
    if row is None:
        return

    settings_table = sa.table(
        "settings",
        sa.column("key", sa.String()),
        sa.column("value", sa.Text()),
    )
    bind.execute(
        sa.insert(settings_table),
        [
            {"key": "site_title", "value": row["site_title"] or ""},
            {"key": "article_page_title", "value": row["article_page_title"] or ""},
            {"key": "icp", "value": row["icp"] or ""},
            {"key": "copyright", "value": row["copyright"] or ""},
            {"key": "link_size", "value": row["link_size"] or ""},
            {"key": "timezone", "value": row["timezone"] or ""},
            {"key": "github_url", "value": row["github_url"] or ""},
            {"key": "analytics_code", "value": row["analytics_code"] or ""},
            {
                "key": "protected_article_paths",
                "value": row["protected_article_paths_json"] or "[]",
            },
        ],
    )
