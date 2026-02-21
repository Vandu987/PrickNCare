"""Add notification_logs table — task 10.1.

Revision ID: task101_notification_logs
Revises: task94_verify
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "task101_notification_logs"
down_revision = "task94_verify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recipient_phone", sa.String(20), nullable=True),
        sa.Column("recipient_email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("message_content", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_notification_logs_recipient_id",
        "notification_logs",
        ["recipient_id"],
    )
    op.create_index(
        "ix_notification_logs_type_status",
        "notification_logs",
        ["notification_type", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_logs_type_status", table_name="notification_logs")
    op.drop_index("ix_notification_logs_recipient_id", table_name="notification_logs")
    op.drop_table("notification_logs")
