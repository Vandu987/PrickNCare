"""Add reconciliation verification and submission fields — task 9.4.

Revision ID: task94_verify
Revises: add_reconciliation_tables_9_3
"""

import sqlalchemy as sa

from alembic import op

revision = "task94_verify"
down_revision = "9a3b4c5d6e7f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add phlebotomist submission fields
    op.add_column(
        "reconciliations",
        sa.Column("submitted_cash", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "reconciliations",
        sa.Column("submitted_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "reconciliations",
        sa.Column(
            "submitted_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "reconciliations",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add verification fields
    op.add_column(
        "reconciliations",
        sa.Column(
            "verified_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "reconciliations",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add PENDING_REVIEW to the enum
    op.execute(
        "ALTER TYPE reconciliation_status ADD VALUE IF NOT EXISTS 'pending_review'"
    )


def downgrade() -> None:
    op.drop_column("reconciliations", "verified_at")
    op.drop_column("reconciliations", "verified_by")
    op.drop_column("reconciliations", "submitted_at")
    op.drop_column("reconciliations", "submitted_by")
    op.drop_column("reconciliations", "submitted_notes")
    op.drop_column("reconciliations", "submitted_cash")
