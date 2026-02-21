"""Add payments table for order payment recording

Revision ID: 9a1b2c3d4e5f
Revises: 8a2b3c4d5e6f
Create Date: 2026-02-22 02:06:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "9a1b2c3d4e5f"
down_revision = "8a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    order_payment_mode = sa.Enum(
        "cash",
        "upi",
        "card",
        "wallet",
        "postpaid",
        name="order_payment_mode",
    )
    order_payment_status = sa.Enum(
        "pending",
        "collected",
        "verified",
        "reconciled",
        name="order_payment_status",
    )
    order_payment_mode.create(op.get_bind(), checkfirst=True)
    order_payment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("mode", order_payment_mode, nullable=False),
        sa.Column(
            "status",
            order_payment_status,
            nullable=False,
            server_default="collected",
        ),
        sa.Column("transaction_ref", sa.String(255), nullable=True),
        sa.Column(
            "collected_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
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
    op.create_index("ix_payments_collected_by", "payments", ["collected_by"])
    op.create_index("ix_payments_collected_at", "payments", ["collected_at"])


def downgrade() -> None:
    op.drop_index("ix_payments_collected_at", table_name="payments")
    op.drop_index("ix_payments_collected_by", table_name="payments")
    op.drop_table("payments")
    op.execute("DROP TYPE IF EXISTS order_payment_mode")
    op.execute("DROP TYPE IF EXISTS order_payment_status")
