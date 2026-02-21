"""NSA (Non-Serviceable Area) record model — task 5.5."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDMixin


class NSARecord(UUIDMixin, Base):
    __tablename__ = "nsa_records"

    pincode: Mapped[str] = mapped_column(
        String(6), unique=True, nullable=False, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    marked_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    marked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("id", uuid.uuid4())  # type: ignore[arg-type]
        kwargs.setdefault("is_active", True)  # type: ignore[arg-type]
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<NSARecord id={self.id} pincode={self.pincode} active={self.is_active}>"
        )
