"""Tests for PricingEngine service — task 7.3."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.pricing import Priority
from app.services.pricing import PricingEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        name="Test Client",
        rate_first_collection=Decimal("150.00"),
        rate_second_collection=Decimal("100.00"),
        rate_priority=Decimal("50.00"),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_package(pkg_id=None, name="CBC", code="CBC001"):
    obj = MagicMock()
    obj.id = pkg_id or uuid.uuid4()
    obj.name = name
    obj.code = code
    obj.base_price = Decimal("200.00")
    obj.is_active = True
    return obj


def _mock_db_execute(client, packages):
    """Return an AsyncMock for db.execute that responds to client & package queries."""
    call_count = 0

    async def _execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Client query
            result.scalar_one_or_none.return_value = client
        else:
            # Package query
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = packages
            result.scalars.return_value = scalars_mock
        return result

    return _execute


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_package_normal_priority():
    client = _make_client()
    pkg = _make_package()
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_mock_db_execute(client, [pkg]))

    engine = PricingEngine(db)
    breakdown = await engine.calculate_order_amount(
        client_id=client.id,
        package_ids=[pkg.id],
        priority=Priority.NORMAL,
    )

    assert breakdown.first_collection_fee == 150.0
    assert breakdown.additional_collection_fees == 0.0
    assert breakdown.priority_fee == 0.0
    assert breakdown.total == 150.0
    assert len(breakdown.packages) == 1


@pytest.mark.asyncio
async def test_multiple_packages_normal_priority():
    client = _make_client()
    pkg1 = _make_package(name="CBC", code="CBC001")
    pkg2 = _make_package(name="LFT", code="LFT001")
    pkg3 = _make_package(name="KFT", code="KFT001")
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_mock_db_execute(client, [pkg1, pkg2, pkg3]))

    engine = PricingEngine(db)
    breakdown = await engine.calculate_order_amount(
        client_id=client.id,
        package_ids=[pkg1.id, pkg2.id, pkg3.id],
        priority=Priority.NORMAL,
    )

    assert breakdown.first_collection_fee == 150.0
    assert breakdown.additional_collection_fees == 200.0  # 100 * 2
    assert breakdown.priority_fee == 0.0
    assert breakdown.total == 350.0
    assert len(breakdown.packages) == 3


@pytest.mark.asyncio
async def test_high_priority():
    client = _make_client()
    pkg = _make_package()
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_mock_db_execute(client, [pkg]))

    engine = PricingEngine(db)
    breakdown = await engine.calculate_order_amount(
        client_id=client.id,
        package_ids=[pkg.id],
        priority=Priority.HIGH,
    )

    assert breakdown.priority_fee == 50.0
    assert breakdown.total == 200.0  # 150 + 50


@pytest.mark.asyncio
async def test_client_not_found():
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    engine = PricingEngine(db)
    with pytest.raises(HTTPException) as exc_info:
        await engine.calculate_order_amount(
            client_id=uuid.uuid4(),
            package_ids=[uuid.uuid4()],
            priority=Priority.NORMAL,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_empty_package_ids():
    db = AsyncMock()
    engine = PricingEngine(db)
    with pytest.raises(HTTPException) as exc_info:
        await engine.calculate_order_amount(
            client_id=uuid.uuid4(),
            package_ids=[],
            priority=Priority.NORMAL,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_package_not_found():
    client = _make_client()
    missing_id = uuid.uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_mock_db_execute(client, []))

    engine = PricingEngine(db)
    with pytest.raises(HTTPException) as exc_info:
        await engine.calculate_order_amount(
            client_id=client.id,
            package_ids=[missing_id],
            priority=Priority.NORMAL,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_line_items_order_matches_input():
    client = _make_client()
    pkg1 = _make_package(name="A", code="A01")
    pkg2 = _make_package(name="B", code="B01")
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_mock_db_execute(client, [pkg1, pkg2]))

    engine = PricingEngine(db)
    breakdown = await engine.calculate_order_amount(
        client_id=client.id,
        package_ids=[pkg1.id, pkg2.id],
        priority=Priority.NORMAL,
    )

    assert breakdown.packages[0].fee == 150.0  # first collection rate
    assert breakdown.packages[1].fee == 100.0  # second collection rate
