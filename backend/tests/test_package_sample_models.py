"""Unit tests for Package, OrderPackage, SampleAccessioning models — task 2.6."""

import uuid

import pytest

from app.models.packages import OrderPackage, Package
from app.models.samples import SampleAccessioning, SampleIntegrity, SampleStatus


class TestPackageModel:
    def _make_package(self, **kwargs: object) -> Package:
        defaults = {"name": "CBC Panel", "code": f"CBC-{uuid.uuid4().hex[:4].upper()}"}
        defaults.update(kwargs)
        return Package(**defaults)  # type: ignore[arg-type]

    def test_uuid_primary_key_auto_generated(self) -> None:
        p = self._make_package()
        assert p.id is not None
        assert isinstance(uuid.UUID(str(p.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        p1 = self._make_package(code="CBC001")
        p2 = self._make_package(code="CBC002")
        assert p1.id != p2.id

    def test_is_active_defaults_to_true(self) -> None:
        p = self._make_package()
        assert p.is_active is True

    def test_base_price_defaults_to_zero(self) -> None:
        p = self._make_package()
        assert p.base_price == 0

    def test_sample_types_defaults_to_empty_list(self) -> None:
        p = self._make_package()
        assert p.sample_types == []

    def test_sample_types_can_be_set(self) -> None:
        p = self._make_package(sample_types=["serum", "plasma"])
        assert p.sample_types == ["serum", "plasma"]

    def test_code_is_unique_and_indexed(self) -> None:
        col = Package.__table__.c["code"]
        assert col.unique is True
        assert col.index is True

    def test_is_active_index_defined(self) -> None:
        index_names = {idx.name for idx in Package.__table__.indexes}
        assert "ix_packages_is_active" in index_names

    def test_table_name(self) -> None:
        assert Package.__tablename__ == "packages"

    def test_repr(self) -> None:
        p = self._make_package(code="HBA1C", name="HbA1c Test")
        r = repr(p)
        assert "Package" in r
        assert "HBA1C" in r
        assert "HbA1c Test" in r


class TestOrderPackageModel:
    def test_composite_primary_key(self) -> None:
        oid = uuid.uuid4()
        pid = uuid.uuid4()
        op = OrderPackage(order_id=oid, package_id=pid)
        assert op.order_id == oid
        assert op.package_id == pid

    def test_quantity_defaults_to_one(self) -> None:
        op = OrderPackage(order_id=uuid.uuid4(), package_id=uuid.uuid4())
        assert op.quantity == 1

    def test_amount_defaults_to_zero(self) -> None:
        op = OrderPackage(order_id=uuid.uuid4(), package_id=uuid.uuid4())
        assert op.amount == 0

    def test_quantity_can_be_set(self) -> None:
        op = OrderPackage(order_id=uuid.uuid4(), package_id=uuid.uuid4(), quantity=3)
        assert op.quantity == 3

    def test_table_name(self) -> None:
        assert OrderPackage.__tablename__ == "order_packages"

    def test_repr(self) -> None:
        oid = uuid.uuid4()
        pid = uuid.uuid4()
        op = OrderPackage(order_id=oid, package_id=pid, quantity=2)
        r = repr(op)
        assert "OrderPackage" in r
        assert "2" in r


class TestSampleIntegrityEnum:
    def test_all_values(self) -> None:
        assert SampleIntegrity.OK == "ok"
        assert SampleIntegrity.LIPEMIC == "lipemic"
        assert SampleIntegrity.LEAKED == "leaked"
        assert SampleIntegrity.HEMOLYZED == "hemolyzed"
        assert SampleIntegrity.CLOTTED == "clotted"
        assert SampleIntegrity.INSUFFICIENT == "insufficient"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            SampleIntegrity("bad")


class TestSampleStatusEnum:
    def test_all_values(self) -> None:
        assert SampleStatus.ACCEPTED == "accepted"
        assert SampleStatus.HOLD == "hold"
        assert SampleStatus.REJECTED == "rejected"


class TestSampleAccessioningModel:
    def _make_sample(self, **kwargs: object) -> SampleAccessioning:
        defaults = {"order_id": uuid.uuid4(), "vial_type": "Red Top"}
        defaults.update(kwargs)
        return SampleAccessioning(**defaults)  # type: ignore[arg-type]

    def test_uuid_primary_key_auto_generated(self) -> None:
        s = self._make_sample()
        assert s.id is not None
        assert isinstance(uuid.UUID(str(s.id)), uuid.UUID)

    def test_quantity_defaults_to_one(self) -> None:
        s = self._make_sample()
        assert s.quantity == 1

    def test_integrity_defaults_to_ok(self) -> None:
        s = self._make_sample()
        assert s.integrity == SampleIntegrity.OK

    def test_status_defaults_to_accepted(self) -> None:
        s = self._make_sample()
        assert s.status == SampleStatus.ACCEPTED

    def test_rejection_reason_optional(self) -> None:
        s = self._make_sample()
        assert s.rejection_reason is None

    def test_received_by_optional(self) -> None:
        s = self._make_sample()
        assert s.received_by is None

    def test_received_at_optional(self) -> None:
        s = self._make_sample()
        assert s.received_at is None

    def test_rejected_status_can_have_reason(self) -> None:
        s = self._make_sample(
            status=SampleStatus.REJECTED, rejection_reason="Sample insufficient"
        )
        assert s.status == SampleStatus.REJECTED
        assert s.rejection_reason == "Sample insufficient"

    def test_hold_status(self) -> None:
        s = self._make_sample(status=SampleStatus.HOLD)
        assert s.status == SampleStatus.HOLD

    def test_lipemic_integrity(self) -> None:
        s = self._make_sample(integrity=SampleIntegrity.LIPEMIC)
        assert s.integrity == SampleIntegrity.LIPEMIC

    def test_table_name(self) -> None:
        assert SampleAccessioning.__tablename__ == "sample_accessionings"

    def test_status_index_defined(self) -> None:
        index_names = {idx.name for idx in SampleAccessioning.__table__.indexes}
        assert "ix_sample_accessionings_status" in index_names

    def test_repr(self) -> None:
        s = self._make_sample()
        r = repr(s)
        assert "SampleAccessioning" in r
        assert "accepted" in r
