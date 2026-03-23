"""drop analytics_code from site settings

Revision ID: 20260324_03
Revises: 20260324_02
Create Date: 2026-03-24 02:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260324_03"
down_revision = "20260324_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "site_settings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("site_settings")}
    if "analytics_code" not in columns:
        return

    with op.batch_alter_table("site_settings") as batch_op:
        batch_op.drop_column("analytics_code")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "site_settings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("site_settings")}
    if "analytics_code" in columns:
        return

    with op.batch_alter_table("site_settings") as batch_op:
        batch_op.add_column(sa.Column("analytics_code", sa.Text(), nullable=False, server_default=""))
