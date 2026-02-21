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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .orders import Order
    from .phlebotomists import Phlebotomist
    from .users import User


class OrderPaymentMode(str, enum.Enum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    WALLET = "wallet"
    POSTPAID = "postpaid"


class OrderPaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COLLECTED = "collected"
    VERIFIED = "verified"
    RECONCILED = "reconciled"


class Payment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    mode: Mapped[OrderPaymentMode] = mapped_column(
        Enum(OrderPaymentMode, name="order_payment_mode"),
        nullable=False,
    )
    status: Mapped[OrderPaymentStatus] = mapped_column(
        Enum(OrderPaymentStatus, name="order_payment_status"),
        nullable=False,
        default=OrderPaymentStatus.COLLECTED,
    )
    transaction_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collected_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", foreign_keys=[order_id])
    collector: Mapped["User"] = relationship("User", foreign_keys=[collected_by])

    __table_args__ = (
        Index("ix_payments_collected_by", "collected_by"),
        Index("ix_payments_collected_at", "collected_at"),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", OrderPaymentStatus.COLLECTED)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Payment {self.id} order={self.order_id} amount={self.amount}>"


class DiscrepancyType(str, enum.Enum):
    SHORTAGE = "shortage"
    EXCESS = "excess"
    NONE = "none"


class PhlebotomistCashReconciliation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "phlebotomist_cash_reconciliations"

    phlebotomist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("phlebotomists.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_appointments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Money fields (all Decimal 10,2)
    cash_collected: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    online_collected: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    handed_over: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )

    # Discrepancy tracking
    discrepancy_amount: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    discrepancy_type: Mapped[DiscrepancyType | None] = mapped_column(
        Enum(DiscrepancyType, name="discrepancy_type"), nullable=True
    )
    discrepancy_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    phlebotomist: Mapped["Phlebotomist"] = relationship(
        "Phlebotomist",
        foreign_keys=[phlebotomist_id],
    )
    verified_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[verified_by]
    )

    __table_args__ = (
        UniqueConstraint(
            "phlebotomist_id",
            "date",
            name="uq_cash_reconciliation_phlebotomist_date",
        ),
        Index("ix_cash_reconciliation_phlebotomist_date", "phlebotomist_id", "date"),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("total_appointments", 0)
        kwargs.setdefault("cash_collected", 0)
        kwargs.setdefault("online_collected", 0)
        kwargs.setdefault("handed_over", 0)
        super().__init__(**kwargs)

    @hybrid_property
    def is_verified(self) -> bool:
        """True when a verifier has signed off the reconciliation."""
        return self.verified_at is not None

    def __repr__(self) -> str:
        return (
            f"<PhlebotomistCashReconciliation"
            f" phlebotomist={self.phlebotomist_id} date={self.date}>"
        )
