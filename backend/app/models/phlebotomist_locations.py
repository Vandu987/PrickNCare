"""Phlebotomist location tracking — task 4.6."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDMixin


class PhlebotomistLocation(UUIDMixin, Base):
    __tablename__ = "phlebotomist_locations"

    phlebotomist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("phlebotomists.id", ondelete="CASCADE"),
        nullable=False,
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_phlebotomist_locations_phleb_recorded",
            "phlebotomist_id",
            "recorded_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PhlebotomistLocation id={self.id}"
            f" phlebotomist_id={self.phlebotomist_id}>"
        )
