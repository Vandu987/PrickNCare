import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .users import User


class PaymentTerms(str, enum.Enum):
    PREPAID = "prepaid"
    POSTPAID = "postpaid"
    WALLET = "wallet"


class Client(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gst_number: Mapped[str | None] = mapped_column(
        String(15), unique=True, nullable=True
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(6), nullable=True)

    # Payment configuration
    payment_terms: Mapped[PaymentTerms] = mapped_column(
        Enum(PaymentTerms, name="payment_terms"),
        nullable=False,
        default=PaymentTerms.PREPAID,
    )
    credit_limit: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
    )

    # Rate fields (per-collection pricing)
    rate_first_collection: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    rate_second_collection: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    rate_priority: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    client_users: Mapped[list["ClientUser"]] = relationship(
        "ClientUser", back_populates="client", cascade="all, delete-orphan"
    )
    created_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by]
    )

    __table_args__ = (Index("ix_clients_is_active", "is_active"),)

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("payment_terms", PaymentTerms.PREPAID)
        kwargs.setdefault("credit_limit", 0)
        kwargs.setdefault("rate_first_collection", 0)
        kwargs.setdefault("rate_second_collection", 0)
        kwargs.setdefault("rate_priority", 0)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<Client id={self.id} name={self.name} terms={self.payment_terms.value}>"
        )


class ClientUser(UUIDMixin, Base):
    __tablename__ = "client_users"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="client_users")
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "client_id", "user_id", name="uq_client_users_client_id_user_id"
        ),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("is_primary", False)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<ClientUser client={self.client_id}"
            f" user={self.user_id} primary={self.is_primary}>"
        )
