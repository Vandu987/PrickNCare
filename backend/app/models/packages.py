import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .orders import Order


class SampleType(enum.StrEnum):
    BLOOD_EDTA = "BLOOD_EDTA"
    BLOOD_SST = "BLOOD_SST"
    BLOOD_FLUORIDE = "BLOOD_FLUORIDE"
    URINE = "URINE"
    STOOL = "STOOL"
    SWAB = "SWAB"


class Package(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "packages"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    preparation_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    tat_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    # JSON array of sample type strings e.g. ["BLOOD_EDTA", "URINE"]
    sample_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, default=None, index=True
    )  # NULL = master package, set = client-specific

    # Relationships
    order_packages: Mapped[list["OrderPackage"]] = relationship(
        "OrderPackage", back_populates="package"
    )

    __table_args__ = (Index("ix_packages_is_active", "is_active"),)

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("base_price", 0)
        kwargs.setdefault("sample_types", [])
        kwargs.setdefault("tat_hours", 24)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Package id={self.id} code={self.code} name={self.name}>"


class OrderPackage(Base):
    __tablename__ = "order_packages"

    # Composite primary key
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        primary_key=True,
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="packages")
    package: Mapped["Package"] = relationship(
        "Package", back_populates="order_packages"
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("quantity", 1)
        kwargs.setdefault("amount", 0)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<OrderPackage order={self.order_id}"
            f" package={self.package_id} qty={self.quantity}>"
        )
