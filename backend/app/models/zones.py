import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .phlebotomists import PhlebotomistZoneAssignment


class City(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cities"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    is_serviceable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    zones: Mapped[list["Zone"]] = relationship(
        "Zone", back_populates="city", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_cities_is_serviceable", "is_serviceable"),)

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("is_serviceable", True)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<City id={self.id} name={self.name} state={self.state}>"


class Zone(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "zones"

    city_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    city: Mapped["City"] = relationship("City", back_populates="zones")
    pincodes: Mapped[list["Pincode"]] = relationship(
        "Pincode", back_populates="zone", cascade="all, delete-orphan"
    )
    phlebotomist_assignments: Mapped[list["PhlebotomistZoneAssignment"]] = relationship(
        "PhlebotomistZoneAssignment",
        primaryjoin="Zone.id == foreign(PhlebotomistZoneAssignment.zone_id)",
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint("city_id", "name", name="uq_zones_city_id_name"),
        Index("ix_zones_is_active", "is_active"),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("is_active", True)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Zone id={self.id} name={self.name} city={self.city_id}>"


class Pincode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pincodes"

    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    pincode: Mapped[str] = mapped_column(
        String(6), unique=True, nullable=False, index=True
    )

    # Relationships
    zone: Mapped["Zone"] = relationship("Zone", back_populates="pincodes")
    localities: Mapped[list["Locality"]] = relationship(
        "Locality", back_populates="pincode", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Pincode id={self.id} pincode={self.pincode} zone={self.zone_id}>"


class Locality(UUIDMixin, Base):
    __tablename__ = "localities"

    pincode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pincodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    pincode: Mapped["Pincode"] = relationship("Pincode", back_populates="localities")

    __table_args__ = (
        UniqueConstraint("pincode_id", "name", name="uq_localities_pincode_id_name"),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Locality id={self.id} name={self.name} pincode={self.pincode_id}>"
