"""Unit tests for PhlebotomistCashReconciliation model — task 2.7."""

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.payments import DiscrepancyType, PhlebotomistCashReconciliation


def _make_reconciliation(**kwargs: object) -> PhlebotomistCashReconciliation:
    defaults = {
        "phlebotomist_id": uuid.uuid4(),
        "date": date(2026, 3, 1),
    }
    defaults.update(kwargs)
    return PhlebotomistCashReconciliation(**defaults)  # type: ignore[arg-type]


class TestDiscrepancyTypeEnum:
    def test_all_values(self) -> None:
        assert DiscrepancyType.SHORTAGE == "shortage"
        assert DiscrepancyType.EXCESS == "excess"
        assert DiscrepancyType.NONE == "none"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            DiscrepancyType("invalid")


class TestPhlebotomistCashReconciliation:
    def test_uuid_primary_key_auto_generated(self) -> None:
        r = _make_reconciliation()
        assert r.id is not None
        assert isinstance(uuid.UUID(str(r.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        r1 = _make_reconciliation()
        r2 = _make_reconciliation()
        assert r1.id != r2.id

    def test_money_fields_default_to_zero(self) -> None:
        r = _make_reconciliation()
        assert r.cash_collected == 0
        assert r.online_collected == 0
        assert r.handed_over == 0

    def test_total_appointments_defaults_to_zero(self) -> None:
        r = _make_reconciliation()
        assert r.total_appointments == 0

    def test_discrepancy_fields_optional(self) -> None:
        r = _make_reconciliation()
        assert r.discrepancy_amount is None
        assert r.discrepancy_type is None
        assert r.discrepancy_notes is None

    def test_verified_by_optional(self) -> None:
        r = _make_reconciliation()
        assert r.verified_by is None

    def test_verified_at_optional(self) -> None:
        r = _make_reconciliation()
        assert r.verified_at is None

    def test_is_verified_false_when_not_verified(self) -> None:
        r = _make_reconciliation()
        assert r.is_verified is False

    def test_is_verified_true_when_verified_at_set(self) -> None:
        r = _make_reconciliation(verified_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC))
        assert r.is_verified is True

    def test_shortage_discrepancy(self) -> None:
        r = _make_reconciliation(
            cash_collected=500,
            handed_over=450,
            discrepancy_amount=50,
            discrepancy_type=DiscrepancyType.SHORTAGE,
            discrepancy_notes="Missing 50 rupees",
        )
        assert r.discrepancy_type == DiscrepancyType.SHORTAGE
        assert r.discrepancy_amount == 50
        assert r.discrepancy_notes == "Missing 50 rupees"

    def test_excess_discrepancy(self) -> None:
        r = _make_reconciliation(
            discrepancy_type=DiscrepancyType.EXCESS,
            discrepancy_amount=20,
        )
        assert r.discrepancy_type == DiscrepancyType.EXCESS

    def test_table_name(self) -> None:
        assert (
            PhlebotomistCashReconciliation.__tablename__
            == "phlebotomist_cash_reconciliations"
        )

    def test_unique_constraint_phlebotomist_date(self) -> None:
        constraint_names = {
            c.name for c in PhlebotomistCashReconciliation.__table__.constraints
        }
        assert "uq_cash_reconciliation_phlebotomist_date" in constraint_names

    def test_composite_index_defined(self) -> None:
        index_names = {
            idx.name for idx in PhlebotomistCashReconciliation.__table__.indexes
        }
        assert "ix_cash_reconciliation_phlebotomist_date" in index_names

    def test_repr(self) -> None:
        pid = uuid.uuid4()
        r = _make_reconciliation(phlebotomist_id=pid, date=date(2026, 3, 15))
        rep = repr(r)
        assert "PhlebotomistCashReconciliation" in rep
        assert "2026-03-15" in rep
