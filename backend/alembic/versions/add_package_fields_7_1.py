"""Add description, preparation_instructions, tat_hours to packages

Revision ID: 7a1b2c3d4e5f
Revises: cc0cbcff92ab
Create Date: 2026-02-22 01:48:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "7a1b2c3d4e5f"
down_revision = "cc0cbcff92ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("packages", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "packages",
        sa.Column("preparation_instructions", sa.Text(), nullable=True),
    )
    op.add_column(
        "packages",
        sa.Column("tat_hours", sa.Integer(), nullable=False, server_default="24"),
    )


def downgrade() -> None:
    op.drop_column("packages", "tat_hours")
    op.drop_column("packages", "preparation_instructions")
    op.drop_column("packages", "description")
