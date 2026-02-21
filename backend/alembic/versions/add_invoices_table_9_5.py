"""Add invoices and invoice_line_items tables

Revision ID: 9a5b6c7d8e9f
Revises: 9a1b2c3d4e5f
Create Date: 2026-02-22 02:06:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "9a5b6c7d8e9f"
down_revision = "9a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create invoice_status enum
    invoice_status_enum = sa.Enum("pending", "paid", name="invoice_status")
    invoice_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False
        ),
        sa.Column("invoice_number", sa.String(50), unique=True, nullable=False),
        sa.Column("date_from", sa.Date, nullable=False),
        sa.Column("date_to", sa.Date, nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("pending", "paid", name="invoice_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("payment_ref", sa.String(255), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_invoices_client_id", "invoices", ["client_id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])
    op.create_index("ix_invoices_client_status", "invoices", ["client_id", "status"])

    op.create_table(
        "invoice_line_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_invoice_line_items_invoice_id", "invoice_line_items", ["invoice_id"]
    )


def downgrade() -> None:
    op.drop_table("invoice_line_items")
    op.drop_table("invoices")
    sa.Enum(name="invoice_status").drop(op.get_bind(), checkfirst=True)
