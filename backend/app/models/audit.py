import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin

if TYPE_CHECKING:
    from .users import User


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"

    # Who performed the action (nullable for system actions)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # What happened
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # create|update|delete|login|logout|…

    # Which entity was affected
    entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "Order", "Client"
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Change tracking (JSON blobs)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_method: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="UNKNOWN"
    )
    request_path: Mapped[str] = mapped_column(
        String(500), nullable=False, server_default="/"
    )
    response_status: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    # Timestamp (only created_at — audit logs are immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_user_id", "user_id"),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id}"
            f" action={self.action} entity={self.entity_type}>"
        )
