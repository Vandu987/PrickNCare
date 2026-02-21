"""API tests for phlebotomist performance report — task 14.2."""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────

PHLEB_ID_1 = uuid.uuid4()
PHLEB_ID_2 = uuid.uuid4()
USER_ID_1 = uuid.uuid4()
USER_ID_2 = uuid.uuid4()
DATE_FROM = "2026-02-01"
DATE_TO = "2026-02-28"
URL = "/api/v1/reports/phlebotomist-performance"


@pytest.fixture(autouse=True)
def mock_rate_limit():
    with patch(
        "app.middleware.rate_limit._sliding_window_check",
        new_callable=AsyncMock,
        return_value=(True, 99, int(time.time()) + 60),
    ):
        yield


def _fake_user(role: UserRole = UserRole.SUPER_ADMIN) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _mock_db_for_performance(
    count_rows=None,
    phleb_rows=None,
    tat_rows=None,
    phleb_user_rows=None,
    earnings_rows=None,
):
    """Build a mock db that returns different results for sequential execute() calls."""
    db = AsyncMock()
    results = []

    # 1) count query
    r1 = MagicMock()
    r1.all.return_value = count_rows or []
    results.append(r1)

    if count_rows:
        # 2) phleb names
        r2 = MagicMock()
        r2.all.return_value = phleb_rows or []
        results.append(r2)

        # 3) TAT
        r3 = MagicMock()
        r3.all.return_value = tat_rows or []
        results.append(r3)

        # 4) phleb→user mapping
        r4 = MagicMock()
        r4.all.return_value = phleb_user_rows or []
        results.append(r4)

        # 5) earnings
        if phleb_user_rows:
            r5 = MagicMock()
            r5.all.return_value = earnings_rows or []
            results.append(r5)

    db.execute.side_effect = results
    return db


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPhlebotomistPerformanceReport:
    async def setup_method(self, method):
        _clear_overrides()

    async def teardown_method(self, method):
        _clear_overrides()

    async def test_success_with_data(self) -> None:
        _override_auth(_fake_user(UserRole.SUPER_ADMIN))

        from app.core.database import get_db

        mock_db = _mock_db_for_performance(
            count_rows=[
                (PHLEB_ID_1, 10, 8),
                (PHLEB_ID_2, 5, 3),
            ],
            phleb_rows=[
                (PHLEB_ID_1, "Alice Phleb"),
                (PHLEB_ID_2, "Bob Phleb"),
            ],
            tat_rows=[
                (PHLEB_ID_1, 3600.0),  # 60 min
                (PHLEB_ID_2, 1800.0),  # 30 min
            ],
            phleb_user_rows=[
                (PHLEB_ID_1, USER_ID_1),
                (PHLEB_ID_2, USER_ID_2),
            ],
            earnings_rows=[
                (USER_ID_1, Decimal("5000.00")),
                (USER_ID_2, Decimal("2500.50")),
            ],
        )
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                URL, params={"date_from": DATE_FROM, "date_to": DATE_TO}
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["date_from"] == DATE_FROM
        assert data["date_to"] == DATE_TO
        assert len(data["phlebotomists"]) == 2

        p1 = data["phlebotomists"][0]
        assert p1["total_collections"] == 10
        assert p1["completed"] == 8
        assert p1["success_rate"] == 80.0
        assert p1["average_tat_minutes"] == 60.0
        assert p1["earnings"] == 5000.00

    async def test_empty_report(self) -> None:
        _override_auth(_fake_user(UserRole.SUPER_ADMIN))

        from app.core.database import get_db

        mock_db = _mock_db_for_performance(count_rows=[])
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                URL, params={"date_from": DATE_FROM, "date_to": DATE_TO}
            )

        assert resp.status_code == 200
        assert resp.json()["phlebotomists"] == []

    async def test_city_admin_allowed(self) -> None:
        _override_auth(_fake_user(UserRole.CITY_ADMIN))

        from app.core.database import get_db

        mock_db = _mock_db_for_performance(count_rows=[])
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                URL, params={"date_from": DATE_FROM, "date_to": DATE_TO}
            )

        assert resp.status_code == 200

    async def test_client_user_forbidden(self) -> None:
        _override_auth(_fake_user(UserRole.CLIENT_USER))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                URL, params={"date_from": DATE_FROM, "date_to": DATE_TO}
            )

        assert resp.status_code == 403

    async def test_phlebotomist_forbidden(self) -> None:
        _override_auth(_fake_user(UserRole.PHLEBOTOMIST))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                URL, params={"date_from": DATE_FROM, "date_to": DATE_TO}
            )

        assert resp.status_code == 403

    async def test_missing_date_params(self) -> None:
        _override_auth(_fake_user(UserRole.SUPER_ADMIN))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(URL)

        assert resp.status_code == 422

    async def test_with_phlebotomist_id_filter(self) -> None:
        _override_auth(_fake_user(UserRole.SUPER_ADMIN))

        from app.core.database import get_db

        mock_db = _mock_db_for_performance(count_rows=[])
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                URL,
                params={
                    "date_from": DATE_FROM,
                    "date_to": DATE_TO,
                    "phlebotomist_id": str(PHLEB_ID_1),
                },
            )

        assert resp.status_code == 200

    async def test_with_city_id_filter(self) -> None:
        _override_auth(_fake_user(UserRole.SUPER_ADMIN))

        from app.core.database import get_db

        mock_db = _mock_db_for_performance(count_rows=[])
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                URL,
                params={
                    "date_from": DATE_FROM,
                    "date_to": DATE_TO,
                    "city_id": str(uuid.uuid4()),
                },
            )

        assert resp.status_code == 200

    async def test_null_tat_when_no_collected_orders(self) -> None:
        _override_auth(_fake_user(UserRole.SUPER_ADMIN))

        from app.core.database import get_db

        mock_db = _mock_db_for_performance(
            count_rows=[(PHLEB_ID_1, 3, 0)],
            phleb_rows=[(PHLEB_ID_1, "No Collections")],
            tat_rows=[],  # no TAT data
            phleb_user_rows=[(PHLEB_ID_1, USER_ID_1)],
            earnings_rows=[],
        )
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                URL, params={"date_from": DATE_FROM, "date_to": DATE_TO}
            )

        assert resp.status_code == 200
        p = resp.json()["phlebotomists"][0]
        assert p["average_tat_minutes"] is None
        assert p["success_rate"] == 0.0
        assert p["earnings"] == 0.0
