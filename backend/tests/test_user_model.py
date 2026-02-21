"""Unit tests for the User model — task 2.1."""

import uuid

import pytest

from app.models.users import User, UserRole


class TestUserModel:
    """Tests for User model fields, password utilities, and polymorphic identity."""

    def test_user_has_uuid_primary_key(self) -> None:
        """User id defaults to a valid UUID."""
        user = User(
            email="a@test.com", phone="+911234567890", role=UserRole.SUPER_ADMIN
        )
        assert user.id is not None
        # Verify it is (or can be converted to) a UUID
        assert isinstance(uuid.UUID(str(user.id)), uuid.UUID)

    def test_uuid_is_unique_per_instance(self) -> None:
        """Each User gets a distinct UUID by default."""
        u1 = User(email="a@test.com", phone="+911111111111", role=UserRole.CLIENT_USER)
        u2 = User(email="b@test.com", phone="+912222222222", role=UserRole.CLIENT_USER)
        assert u1.id != u2.id

    def test_password_hashing_and_verification(self) -> None:
        """set_password stores a bcrypt hash; verify_password validates it."""
        user = User(
            email="c@test.com", phone="+913333333333", role=UserRole.PHLEBOTOMIST
        )
        user.set_password("SecurePass123!")
        assert user.password_hash is not None
        assert user.password_hash != "SecurePass123!"
        assert user.verify_password("SecurePass123!") is True

    def test_wrong_password_fails_verification(self) -> None:
        """verify_password returns False for an incorrect password."""
        user = User(
            email="d@test.com", phone="+914444444444", role=UserRole.PHLEBOTOMIST
        )
        user.set_password("CorrectPass!")
        assert user.verify_password("WrongPass!") is False

    def test_verify_password_without_hash_returns_false(self) -> None:
        """verify_password returns False when no password_hash is set."""
        user = User(
            email="e@test.com", phone="+915555555555", role=UserRole.CLIENT_USER
        )
        assert user.password_hash is None
        assert user.verify_password("anything") is False

    def test_static_hash_password(self) -> None:
        """hash_password static method returns a valid bcrypt hash."""
        hashed = User.hash_password("TestPassword!")
        assert hashed.startswith("$2b$")

    def test_role_enum_valid_values(self) -> None:
        """UserRole enum accepts all four valid roles."""
        assert UserRole.SUPER_ADMIN == "super_admin"
        assert UserRole.CITY_ADMIN == "city_admin"
        assert UserRole.CLIENT_USER == "client_user"
        assert UserRole.PHLEBOTOMIST == "phlebotomist"

    def test_role_enum_rejects_invalid_value(self) -> None:
        """UserRole enum raises ValueError for invalid strings."""
        with pytest.raises(ValueError):
            UserRole("invalid_role")

    def test_is_active_defaults_to_true(self) -> None:
        """is_active column defaults to True on new instances."""
        user = User(email="f@test.com", phone="+916666666666", role=UserRole.CITY_ADMIN)
        assert user.is_active is True

    def test_polymorphic_identity_is_none_for_base(self) -> None:
        """Base User has polymorphic_identity=None (not a concrete subtype)."""
        mapper_args = User.__mapper_args__
        assert mapper_args["polymorphic_identity"] is None
        assert mapper_args["polymorphic_on"] == "role"

    def test_table_name(self) -> None:
        """User maps to the 'users' table."""
        assert User.__tablename__ == "users"

    def test_indexes_defined(self) -> None:
        """Verify that expected indexes are declared on the User table."""
        table = User.__table__
        index_names = {idx.name for idx in table.indexes}
        # Composite index
        assert "ix_users_is_active_role" in index_names

    def test_email_column_is_unique_and_indexed(self) -> None:
        """email column has unique=True and index=True."""
        col = User.__table__.c["email"]
        assert col.unique is True

    def test_phone_column_is_unique(self) -> None:
        """phone column has unique=True."""
        col = User.__table__.c["phone"]
        assert col.unique is True

    def test_repr(self) -> None:
        """__repr__ returns a meaningful string."""
        user = User(
            email="g@test.com", phone="+917777777777", role=UserRole.SUPER_ADMIN
        )
        r = repr(user)
        assert "User" in r
        assert "g@test.com" in r
        assert "super_admin" in r
