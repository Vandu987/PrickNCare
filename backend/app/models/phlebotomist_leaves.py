"""Phlebotomist leave model — task 4.5."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class PhlebotomistLeave(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "phlebotomist_leaves"

    phlebotomist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("phlebotomists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    leave_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="full_day"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<PhlebotomistLeave id={self.id}"
            f" phlebotomist={self.phlebotomist_id} date={self.date}>"
        )
