import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .orders import Order
    from .users import User


class VialType(str, enum.Enum):
    EDTA_PURPLE = "edta_purple"
    SST_YELLOW = "sst_yellow"
    FLUORIDE_GREY = "fluoride_grey"
    URINE_CONTAINER = "urine_container"
    OTHER = "other"


class SampleIntegrity(str, enum.Enum):
    OK = "ok"
    LIPEMIC = "lipemic"
    LEAKED = "leaked"
    HEMOLYZED = "hemolyzed"
    CLOTTED = "clotted"
    INSUFFICIENT = "insufficient"


class SampleStatus(str, enum.Enum):
    ACCEPTED = "accepted"
    HOLD = "hold"
    REJECTED = "rejected"


class SampleAccessioning(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sample_accessionings"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vial_type: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    integrity: Mapped[SampleIntegrity] = mapped_column(
        Enum(SampleIntegrity, name="sample_integrity"),
        nullable=False,
        default=SampleIntegrity.OK,
    )
    status: Mapped[SampleStatus] = mapped_column(
        Enum(SampleStatus, name="sample_status"),
        nullable=False,
        default=SampleStatus.ACCEPTED,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Receiving / accessioning
    accessioned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    received_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="samples")
    received_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[received_by]
    )
    accessioned_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[accessioned_by]
    )

    __table_args__ = (Index("ix_sample_accessionings_status", "status"),)

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("quantity", 1)
        kwargs.setdefault("integrity", SampleIntegrity.OK)
        kwargs.setdefault("status", SampleStatus.ACCEPTED)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<SampleAccessioning id={self.id}"
            f" order={self.order_id} status={self.status.value}>"
        )
