"""Tests for RBAC dependency system — task 3.5."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.deps import (
    RoleChecker,
    get_current_active_user,
    get_current_user,
    require_roles,
)
from app.models.users import User, UserRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(role: UserRole, is_active: bool = True) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = is_active
    return user


def _valid_payload(user: User) -> dict:
    return {"sub": str(user.id), "role": user.role.value, "jti": str(uuid.uuid4())}


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self) -> None:
        user = _make_user(UserRole.CLIENT_USER)
        payload = _valid_payload(user)

        mock_creds = MagicMock()
        mock_creds.credentials = "valid.jwt.token"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.deps.validate_access_token",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            result = await get_current_user(credentials=mock_creds, db=mock_db)

        assert result is user

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self) -> None:
        from jose import JWTError

        mock_creds = MagicMock()
        mock_creds.credentials = "bad.token"
        mock_db = AsyncMock()

        with patch(
            "app.api.deps.validate_access_token",
            new_callable=AsyncMock,
            side_effect=JWTError("bad"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_creds, db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_sub_raises_401(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "token"
        mock_db = AsyncMock()

        with patch(
            "app.api.deps.validate_access_token",
            new_callable=AsyncMock,
            return_value={"role": "client_user"},  # no 'sub'
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_creds, db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_in_db_raises_401(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "token"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.deps.validate_access_token",
            new_callable=AsyncMock,
            return_value={"sub": str(uuid.uuid4())},
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_creds, db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_response_has_www_authenticate_header(self) -> None:
        from jose import JWTError

        mock_creds = MagicMock()
        mock_creds.credentials = "bad"
        mock_db = AsyncMock()

        with patch(
            "app.api.deps.validate_access_token",
            new_callable=AsyncMock,
            side_effect=JWTError("bad"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_creds, db=mock_db)

        assert "WWW-Authenticate" in exc_info.value.headers


# ---------------------------------------------------------------------------
# get_current_active_user
# ---------------------------------------------------------------------------


class TestGetCurrentActiveUser:
    @pytest.mark.asyncio
    async def test_active_user_passes_through(self) -> None:
        user = _make_user(UserRole.CLIENT_USER, is_active=True)
        result = await get_current_active_user(user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_inactive_user_raises_403(self) -> None:
        user = _make_user(UserRole.CLIENT_USER, is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(user=user)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# require_roles
# ---------------------------------------------------------------------------


class TestRequireRoles:
    @pytest.mark.asyncio
    async def test_matching_role_allowed(self) -> None:
        user = _make_user(UserRole.CITY_ADMIN)
        dep = require_roles("city_admin")
        result = await dep(user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_wrong_role_raises_403(self) -> None:
        user = _make_user(UserRole.CLIENT_USER)
        dep = require_roles("city_admin")
        with pytest.raises(HTTPException) as exc_info:
            await dep(user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_super_admin_always_allowed(self) -> None:
        user = _make_user(UserRole.SUPER_ADMIN)
        dep = require_roles("city_admin")  # super_admin not listed
        result = await dep(user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_multiple_roles_any_match(self) -> None:
        phlebotomist = _make_user(UserRole.PHLEBOTOMIST)
        dep = require_roles("city_admin", "phlebotomist")
        result = await dep(user=phlebotomist)
        assert result is phlebotomist

    @pytest.mark.asyncio
    async def test_multiple_roles_no_match_raises_403(self) -> None:
        user = _make_user(UserRole.CLIENT_USER)
        dep = require_roles("city_admin", "phlebotomist")
        with pytest.raises(HTTPException) as exc_info:
            await dep(user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_user_object(self) -> None:
        user = _make_user(UserRole.SUPER_ADMIN)
        dep = require_roles("super_admin")
        result = await dep(user=user)
        assert result is user


# ---------------------------------------------------------------------------
# RoleChecker
# ---------------------------------------------------------------------------


class TestRoleChecker:
    @pytest.mark.asyncio
    async def test_allowed_role_passes(self) -> None:
        checker = RoleChecker("city_admin")
        user = _make_user(UserRole.CITY_ADMIN)
        result = await checker(user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_disallowed_role_raises_403(self) -> None:
        checker = RoleChecker("city_admin")
        user = _make_user(UserRole.CLIENT_USER)
        with pytest.raises(HTTPException) as exc_info:
            await checker(user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_super_admin_always_allowed(self) -> None:
        checker = RoleChecker("phlebotomist")
        user = _make_user(UserRole.SUPER_ADMIN)
        result = await checker(user=user)
        assert result is user

    def test_allowed_roles_property_includes_super_admin(self) -> None:
        checker = RoleChecker("city_admin")
        assert UserRole.SUPER_ADMIN.value in checker.allowed_roles

    def test_allowed_roles_property_includes_specified_roles(self) -> None:
        checker = RoleChecker("city_admin", "phlebotomist")
        assert "city_admin" in checker.allowed_roles
        assert "phlebotomist" in checker.allowed_roles

    @pytest.mark.asyncio
    async def test_multiple_allowed_roles(self) -> None:
        checker = RoleChecker("city_admin", "phlebotomist")
        for role in (UserRole.CITY_ADMIN, UserRole.PHLEBOTOMIST, UserRole.SUPER_ADMIN):
            user = _make_user(role)
            result = await checker(user=user)
            assert result is user

    @pytest.mark.asyncio
    async def test_reusable_instance(self) -> None:
        """Same checker instance works for multiple calls."""
        checker = RoleChecker("super_admin")
        for _ in range(3):
            user = _make_user(UserRole.SUPER_ADMIN)
            result = await checker(user=user)
            assert result is user


# ---------------------------------------------------------------------------
# UserRole enum coverage
# ---------------------------------------------------------------------------


class TestUserRoleEnum:
    def test_all_four_roles_exist(self) -> None:
        roles = {r.value for r in UserRole}
        assert "super_admin" in roles
        assert "city_admin" in roles
        assert "client_user" in roles
        assert "phlebotomist" in roles

    def test_super_admin_value(self) -> None:
        assert UserRole.SUPER_ADMIN.value == "super_admin"
