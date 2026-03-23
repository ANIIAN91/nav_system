"""create core application tables

Revision ID: 20260324_00
Revises:
Create Date: 2026-03-24 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260324_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the non-settings tables that used to be created via Base.metadata.create_all()."""
    bind = op.get_bind()
    metadata = sa.MetaData()

    categories = sa.Table(
        "categories",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("auth_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    links = sa.Table(
        "links",
        metadata,
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    visit_logs = sa.Table(
        "visit_logs",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("path", sa.String(length=500), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    update_logs = sa.Table(
        "update_logs",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("action", sa.String(length=50), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_name", sa.String(length=200), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    token_blacklist = sa.Table(
        "token_blacklist",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("jti", sa.String(length=100), nullable=False, unique=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
    )

    sa.Index("ix_categories_name", categories.c.name)
    sa.Index("ix_links_category_id", links.c.category_id)
    sa.Index("idx_visit_logs_created_at", visit_logs.c.created_at.desc())
    sa.Index("idx_update_logs_created_at", update_logs.c.created_at.desc())
    sa.Index("idx_token_blacklist_jti", token_blacklist.c.jti)
    sa.Index("idx_token_blacklist_expires_at", token_blacklist.c.expires_at)

    metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()

    categories = sa.Table("categories", metadata)
    links = sa.Table("links", metadata)
    visit_logs = sa.Table("visit_logs", metadata)
    update_logs = sa.Table("update_logs", metadata)
    token_blacklist = sa.Table("token_blacklist", metadata)

    for table in (links, token_blacklist, update_logs, visit_logs, categories):
        table.drop(bind=bind, checkfirst=True)
