"""Client rate change history — task 4.2."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class ClientRateHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "client_rate_history"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    new_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    effective_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    __table_args__ = (Index("ix_client_rate_history_client_id", "client_id"),)

    def __repr__(self) -> str:
        return (
            f"<ClientRateHistory client={self.client_id}"
            f" field={self.field_name} {self.previous_value}->{self.new_value}>"
        )
