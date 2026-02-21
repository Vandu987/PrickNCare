"""PhlebotomistDocument model — task 4.4."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .phlebotomists import Phlebotomist
    from .users import User


class PhlebotomistDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "phlebotomist_documents"

    phlebotomist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("phlebotomists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # id_proof / certification / photo
    s3_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
        "Phlebotomist", foreign_keys=[phlebotomist_id]
    )
    verifier: Mapped["User | None"] = relationship("User", foreign_keys=[verified_by])

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("verified", False)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<PhlebotomistDocument id={self.id}"
            f" phlebotomist_id={self.phlebotomist_id} doc_type={self.doc_type}>"
        )
