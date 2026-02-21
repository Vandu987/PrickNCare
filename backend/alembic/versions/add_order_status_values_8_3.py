"""Add COMPLETED, SAMPLE_REJECTED, SAMPLE_HOLD to order_status enum.

Revision ID: task_8_3_status
"""

from alembic import op

revision = "task_8_3_status"
down_revision = None  # standalone — uses IF NOT EXISTS
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'completed'")
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'sample_rejected'")
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'sample_hold'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values; no-op
    pass
