"""Add request_method, request_path, response_status to audit_logs — task 16.1.

Revision ID: task161_audit_fields
Revises: task105_templates
"""

import sqlalchemy as sa

from alembic import op

revision = "task161_audit_fields"
down_revision = "task105_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column(
            "request_method",
            sa.String(length=10),
            server_default="UNKNOWN",
            nullable=False,
        ),
    )
    op.add_column(
        "audit_logs",
        sa.Column(
            "request_path",
            sa.String(length=500),
            server_default="/",
            nullable=False,
        ),
    )
    op.add_column(
        "audit_logs",
        sa.Column(
            "response_status",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("audit_logs", "response_status")
    op.drop_column("audit_logs", "request_path")
    op.drop_column("audit_logs", "request_method")
