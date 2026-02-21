import enum
import uuid
from typing import Any

import bcrypt as _bcrypt
from sqlalchemy import Boolean, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    CITY_ADMIN = "city_admin"
    CLIENT_USER = "client_user"
    PHLEBOTOMIST = "phlebotomist"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # Core identity fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,  # OTP-only login users may not have a password
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Polymorphic configuration — subclasses identify via role column
    __mapper_args__ = {
        "polymorphic_on": "role",
        "polymorphic_identity": None,
    }

    # Composite index on (is_active, role) for active-user-by-role queries
    __table_args__ = (Index("ix_users_is_active_role", "is_active", "role"),)

    def __init__(self, **kwargs: Any) -> None:
        """Apply Python-level defaults before delegating to SQLAlchemy."""
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("is_active", True)
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # Password utilities
    # ------------------------------------------------------------------

    def set_password(self, plain_password: str) -> None:
        """Hash and store a password."""
        self.password_hash = _bcrypt.hashpw(
            plain_password.encode("utf-8"), _bcrypt.gensalt()
        ).decode("utf-8")

    def verify_password(self, plain_password: str) -> bool:
        """Verify a plain-text password against the stored hash."""
        if not self.password_hash:
            return False
        return _bcrypt.checkpw(
            plain_password.encode("utf-8"),
            self.password_hash.encode("utf-8"),
        )

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Return bcrypt hash without storing — useful in services."""
        return _bcrypt.hashpw(plain_password.encode("utf-8"), _bcrypt.gensalt()).decode(
            "utf-8"
        )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role.value}>"
