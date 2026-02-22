"""Add attendance table for phlebotomist check-in/check-out.

Revision ID: add_attendance
Revises: task94_verify
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "add_attendance"
down_revision = "task94_verify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE attendance_status_enum AS ENUM ('checked_in', 'checked_out')
    """)

    op.create_table(
        "attendance",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("date", sa.Date, nullable=False, index=True),
        sa.Column("status", sa.Enum("checked_in", "checked_out", name="attendance_status_enum", create_type=False), nullable=False, server_default="checked_in"),
        sa.Column("check_in_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("check_in_latitude", sa.Float, nullable=False),
        sa.Column("check_in_longitude", sa.Float, nullable=False),
        sa.Column("check_in_location_name", sa.String(255), nullable=True),
        sa.Column("check_out_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_latitude", sa.Float, nullable=True),
        sa.Column("check_out_longitude", sa.Float, nullable=True),
        sa.Column("check_out_location_name", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
    )


def downgrade() -> None:
    op.drop_table("attendance")
    op.execute("DROP TYPE IF EXISTS attendance_status_enum")
