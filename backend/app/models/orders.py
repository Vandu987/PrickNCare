import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .clients import Client
    from .packages import OrderPackage
    from .phlebotomists import Phlebotomist
    from .samples import SampleAccessioning
    from .users import User
    from .zones import Locality, Pincode


class PatientTitle(str, enum.Enum):
    MR = "Mr"
    MRS = "Mrs"
    MS = "Ms"
    DR = "Dr"
    MASTER = "Master"


class PatientGender(str, enum.Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    IN_TRANSIT = "in_transit"
    COLLECTED = "collected"
    UNCOLLECTED = "uncollected"
    CANCELLED = "cancelled"
    NSA = "nsa"  # Not Serviceable Area


class OrderPriority(str, enum.Enum):
    NORMAL = "normal"
    HIGH = "high"


class PaymentMode(str, enum.Enum):
    CASH = "cash"
    ONLINE = "online"
    PREPAID = "prepaid"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COLLECTED = "collected"
    VERIFIED = "verified"


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    booking_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Foreign keys
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pincode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pincodes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    locality_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("localities.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Patient info
    patient_title: Mapped[PatientTitle] = mapped_column(
        Enum(PatientTitle, name="patient_title"), nullable=False
    )
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    patient_age: Mapped[int] = mapped_column(Integer, nullable=False)
    patient_gender: Mapped[PatientGender] = mapped_column(
        Enum(PatientGender, name="patient_gender"), nullable=False
    )
    patient_phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Scheduling
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    appointment_time_slot: Mapped[str] = mapped_column(String(50), nullable=False)

    # Address
    address: Mapped[str] = mapped_column(Text, nullable=False)
    landmark: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True,
    )

    # Priority
    priority: Mapped[OrderPriority] = mapped_column(
        Enum(OrderPriority, name="order_priority"),
        nullable=False,
        default=OrderPriority.NORMAL,
    )
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Payment
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    payment_mode: Mapped[PaymentMode] = mapped_column(
        Enum(PaymentMode, name="payment_mode"),
        nullable=False,
        default=PaymentMode.CASH,
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    # Assignment
    assigned_phlebotomist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("phlebotomists.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Proof
    collection_proof_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    patient_signature_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", foreign_keys=[client_id])
    pincode: Mapped["Pincode"] = relationship("Pincode")
    locality: Mapped["Locality | None"] = relationship("Locality")
    assigned_phlebotomist: Mapped["Phlebotomist | None"] = relationship(
        "Phlebotomist", foreign_keys=[assigned_phlebotomist_id]
    )
    created_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by]
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    packages: Mapped[list["OrderPackage"]] = relationship(
        "OrderPackage", back_populates="order", cascade="all, delete-orphan"
    )
    samples: Mapped[list["SampleAccessioning"]] = relationship(
        "SampleAccessioning", back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_orders_status_date", "status", "appointment_date"),)

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("booking_id", f"BK-{uuid.uuid4().hex[:8].upper()}")
        kwargs.setdefault("status", OrderStatus.PENDING)
        kwargs.setdefault("priority", OrderPriority.NORMAL)
        kwargs.setdefault("amount", 0)
        kwargs.setdefault("payment_mode", PaymentMode.CASH)
        kwargs.setdefault("payment_status", PaymentStatus.PENDING)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<Order id={self.id}"
            f" booking_id={self.booking_id} status={self.status.value}>"
        )


class OrderStatusHistory(UUIDMixin, Base):
    __tablename__ = "order_status_history"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", create_type=False),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="status_history")
    changed_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[changed_by]
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<OrderStatusHistory" f" order={self.order_id} status={self.status.value}>"
        )
