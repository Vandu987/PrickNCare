"""Add notes and accessioned_by to sample_accessionings

Revision ID: 8a2b3c4d5e6f
Revises: 7a1b2c3d4e5f
Create Date: 2026-02-22 01:59:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "8a2b3c4d5e6f"
down_revision = "7a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sample_accessionings", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "sample_accessionings",
        sa.Column("accessioned_by", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_sample_accessionings_accessioned_by_users"),
        "sample_accessionings",
        "users",
        ["accessioned_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_sample_accessionings_accessioned_by_users"),
        "sample_accessionings",
        type_="foreignkey",
    )
    op.drop_column("sample_accessionings", "accessioned_by")
    op.drop_column("sample_accessionings", "notes")
