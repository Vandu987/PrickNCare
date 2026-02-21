"""Reconciliation models — task 9.3."""

from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .phlebotomists import Phlebotomist
    from .users import User


class ReconciliationStatus(enum.StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"


class DiscrepancyCategory(enum.StrEnum):
    FUEL_ALLOWANCE = "fuel_allowance"
    CASH_SHORTAGE = "cash_shortage"
    OVERAGE = "overage"
    PATIENT_REFUND = "patient_refund"
    INCENTIVE_ADJUSTMENT = "incentive_adjustment"
    OTHER = "other"


class Reconciliation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reconciliations"

    phlebotomist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("phlebotomists.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_cash: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cash_handed_over: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    net_discrepancy: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus, name="reconciliation_status"),
        nullable=False,
        default=ReconciliationStatus.CONFIRMED,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    # Relationships
    phlebotomist: Mapped[Phlebotomist] = relationship(
        "Phlebotomist", foreign_keys=[phlebotomist_id]
    )
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])
    discrepancies: Mapped[list[ReconciliationDiscrepancy]] = relationship(
        "ReconciliationDiscrepancy",
        back_populates="reconciliation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "phlebotomist_id", "date", name="uq_reconciliation_phlebotomist_date"
        ),
        Index("ix_reconciliation_phlebotomist_date", "phlebotomist_id", "date"),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", ReconciliationStatus.CONFIRMED)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<Reconciliation {self.id} phleb={self.phlebotomist_id} date={self.date}>"
        )


class ReconciliationDiscrepancy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reconciliation_discrepancies"

    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reconciliations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[DiscrepancyCategory] = mapped_column(
        Enum(DiscrepancyCategory, name="discrepancy_category"),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    reconciliation: Mapped[Reconciliation] = relationship(
        "Reconciliation", back_populates="discrepancies"
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<ReconciliationDiscrepancy {self.id} type={self.type}>"
