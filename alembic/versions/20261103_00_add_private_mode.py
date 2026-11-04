"""add private_mode to site settings

Revision ID: 20261103_00
Revises: 20260324_03
Create Date: 2026-11-03 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20261103_00"
down_revision = "20260324_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "site_settings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("site_settings")}
    if "private_mode" in columns:
        return

    # 默认开启：未登录访客看不到任何导航链接
    with op.batch_alter_table("site_settings") as batch_op:
        batch_op.add_column(
            sa.Column("private_mode", sa.Boolean(), nullable=False, server_default=sa.true())
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "site_settings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("site_settings")}
    if "private_mode" not in columns:
        return

    with op.batch_alter_table("site_settings") as batch_op:
        batch_op.drop_column("private_mode")
