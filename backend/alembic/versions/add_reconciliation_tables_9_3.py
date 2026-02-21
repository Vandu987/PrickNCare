"""Add reconciliation and reconciliation_discrepancies tables

Revision ID: 9a3b4c5d6e7f
Revises: 9a1b2c3d4e5f
Create Date: 2026-02-22 02:13:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "9a3b4c5d6e7f"
down_revision = "9a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    reconciliation_status = sa.Enum(
        "draft", "confirmed", "disputed", name="reconciliation_status"
    )
    discrepancy_category = sa.Enum(
        "fuel_allowance",
        "cash_shortage",
        "overage",
        "patient_refund",
        "incentive_adjustment",
        "other",
        name="discrepancy_category",
    )
    reconciliation_status.create(op.get_bind(), checkfirst=True)
    discrepancy_category.create(op.get_bind(), checkfirst=True)

    # Create reconciliations table
    op.create_table(
        "reconciliations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "phlebotomist_id",
            UUID(as_uuid=True),
            sa.ForeignKey("phlebotomists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("expected_cash", sa.Numeric(10, 2), nullable=False),
        sa.Column("cash_handed_over", sa.Numeric(10, 2), nullable=False),
        sa.Column("net_discrepancy", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status",
            reconciliation_status,
            nullable=False,
            server_default="confirmed",
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "phlebotomist_id", "date", name="uq_reconciliation_phlebotomist_date"
        ),
    )
    op.create_index(
        "ix_reconciliation_phlebotomist_date",
        "reconciliations",
        ["phlebotomist_id", "date"],
    )

    # Create reconciliation_discrepancies table
    op.create_table(
        "reconciliation_discrepancies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reconciliation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("reconciliations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type", discrepancy_category, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("reconciliation_discrepancies")
    op.drop_index("ix_reconciliation_phlebotomist_date", table_name="reconciliations")
    op.drop_table("reconciliations")
    op.execute("DROP TYPE IF EXISTS discrepancy_category")
    op.execute("DROP TYPE IF EXISTS reconciliation_status")
