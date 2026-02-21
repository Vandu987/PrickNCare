import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .users import User


class Phlebotomist(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "phlebotomists"

    # One-to-one link to User
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Personal details
    employee_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Document URLs
    id_proof_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    certification_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Bank details
    bank_account_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(String(11), nullable=True)
    upi_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Working schedule
    working_hours_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    working_hours_end: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Location tracking
    current_location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_location_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    zone_assignments: Mapped[list["PhlebotomistZoneAssignment"]] = relationship(
        "PhlebotomistZoneAssignment",
        back_populates="phlebotomist",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_phlebotomists_is_available", "is_available"),
        Index(
            "ix_phlebotomists_location",
            "is_available",
            "current_location_lat",
            "current_location_lng",
        ),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("is_available", True)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<Phlebotomist id={self.id}"
            f" employee_id={self.employee_id} name={self.name}>"
        )


class PhlebotomistZoneAssignment(Base):
    __tablename__ = "phlebotomist_zone_assignments"

    # Composite primary key
    phlebotomist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("phlebotomists.id", ondelete="CASCADE"),
        primary_key=True,
    )
    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships — zone relationship added when Zone model is defined (task 2.4)
    phlebotomist: Mapped["Phlebotomist"] = relationship(
        "Phlebotomist", back_populates="zone_assignments"
    )

    def __repr__(self) -> str:
        return (
            f"<PhlebotomistZoneAssignment"
            f" phlebotomist={self.phlebotomist_id} zone={self.zone_id}>"
        )
