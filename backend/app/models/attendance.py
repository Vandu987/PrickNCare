"""Attendance model — tracks phlebotomist daily check-in/check-out."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class AttendanceStatus(str, enum.Enum):
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"


class Attendance(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status_enum"),
        nullable=False,
        default=AttendanceStatus.CHECKED_IN,
    )

    check_in_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    check_in_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    check_in_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    check_in_location_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    check_out_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    check_out_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_location_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationship
    user = relationship("User", backref="attendance_records")
