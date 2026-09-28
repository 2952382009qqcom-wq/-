"""Add optional official-source media fields to legal cases.

Revision ID: 20260927_case_library_media
Revises: 20260927_platform_foundations_v2
"""

from alembic import op
import sqlalchemy as sa


revision = "20260927_case_library_media"
down_revision = "20260927_platform_foundations_v2"
branch_labels = None
depends_on = None


def _column_names(table_name):
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    if "legal_cases" not in sa.inspect(op.get_bind()).get_table_names():
        return
    columns = _column_names("legal_cases")
    additions = (
        ("image_url", sa.String(length=1000)),
        ("image_alt", sa.String(length=320)),
        ("image_source_url", sa.String(length=1000)),
    )
    for name, column_type in additions:
        if name not in columns:
            op.add_column(
                "legal_cases",
                sa.Column(name, column_type, nullable=False, server_default=""),
            )


def downgrade():
    if "legal_cases" not in sa.inspect(op.get_bind()).get_table_names():
        return
    columns = _column_names("legal_cases")
    for name in ("image_source_url", "image_alt", "image_url"):
        if name in columns:
            op.drop_column("legal_cases", name)
