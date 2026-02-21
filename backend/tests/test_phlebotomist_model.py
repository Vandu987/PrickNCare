"""Unit tests for Phlebotomist and PhlebotomistZoneAssignment models — task 2.3."""

import uuid
from datetime import time

import pytest

from app.models.phlebotomists import Phlebotomist, PhlebotomistZoneAssignment


class TestPhlebotomistModel:
    def _make_phlebotomist(self, **kwargs: object) -> Phlebotomist:
        defaults = {
            "user_id": uuid.uuid4(),
            "employee_id": f"EMP{uuid.uuid4().hex[:6].upper()}",
            "name": "John Doe",
            "phone": "+911234567890",
        }
        defaults.update(kwargs)
        return Phlebotomist(**defaults)  # type: ignore[arg-type]

    def test_uuid_primary_key_auto_generated(self) -> None:
        p = self._make_phlebotomist()
        assert p.id is not None
        assert isinstance(uuid.UUID(str(p.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        p1 = self._make_phlebotomist(employee_id="EMP001")
        p2 = self._make_phlebotomist(employee_id="EMP002")
        assert p1.id != p2.id

    def test_is_available_defaults_to_true(self) -> None:
        p = self._make_phlebotomist()
        assert p.is_available is True

    def test_is_available_can_be_set_false(self) -> None:
        p = self._make_phlebotomist(is_available=False)
        assert p.is_available is False

    def test_document_urls_default_to_none(self) -> None:
        p = self._make_phlebotomist()
        assert p.id_proof_url is None
        assert p.certification_url is None
        assert p.photo_url is None

    def test_document_urls_can_be_set(self) -> None:
        p = self._make_phlebotomist(
            id_proof_url="https://example.com/id.jpg",
            certification_url="https://example.com/cert.pdf",
            photo_url="https://example.com/photo.jpg",
        )
        assert p.id_proof_url == "https://example.com/id.jpg"
        assert p.certification_url == "https://example.com/cert.pdf"
        assert p.photo_url == "https://example.com/photo.jpg"

    def test_bank_details_default_to_none(self) -> None:
        p = self._make_phlebotomist()
        assert p.bank_account_number is None
        assert p.bank_ifsc is None
        assert p.upi_id is None

    def test_bank_details_can_be_set(self) -> None:
        p = self._make_phlebotomist(
            bank_account_number="123456789012",
            bank_ifsc="SBIN0001234",
            upi_id="john@upi",
        )
        assert p.bank_account_number == "123456789012"
        assert p.bank_ifsc == "SBIN0001234"
        assert p.upi_id == "john@upi"

    def test_working_hours_default_to_none(self) -> None:
        p = self._make_phlebotomist()
        assert p.working_hours_start is None
        assert p.working_hours_end is None

    def test_working_hours_can_be_set(self) -> None:
        p = self._make_phlebotomist(
            working_hours_start=time(8, 0),
            working_hours_end=time(18, 0),
        )
        assert p.working_hours_start == time(8, 0)
        assert p.working_hours_end == time(18, 0)

    def test_location_defaults_to_none(self) -> None:
        p = self._make_phlebotomist()
        assert p.current_location_lat is None
        assert p.current_location_lng is None

    def test_location_can_be_set(self) -> None:
        p = self._make_phlebotomist(
            current_location_lat=19.076,
            current_location_lng=72.877,
        )
        assert p.current_location_lat == pytest.approx(19.076)
        assert p.current_location_lng == pytest.approx(72.877)

    def test_table_name(self) -> None:
        assert Phlebotomist.__tablename__ == "phlebotomists"

    def test_employee_id_is_unique_and_indexed(self) -> None:
        col = Phlebotomist.__table__.c["employee_id"]
        assert col.unique is True
        assert col.index is True

    def test_user_id_is_unique(self) -> None:
        col = Phlebotomist.__table__.c["user_id"]
        assert col.unique is True

    def test_indexes_defined(self) -> None:
        index_names = {idx.name for idx in Phlebotomist.__table__.indexes}
        assert "ix_phlebotomists_is_available" in index_names
        assert "ix_phlebotomists_location" in index_names

    def test_repr(self) -> None:
        p = self._make_phlebotomist(employee_id="EMP999", name="Jane Smith")
        r = repr(p)
        assert "Phlebotomist" in r
        assert "EMP999" in r
        assert "Jane Smith" in r


class TestPhlebotomistZoneAssignment:
    def test_composite_primary_key(self) -> None:
        p_id = uuid.uuid4()
        z_id = uuid.uuid4()
        pza = PhlebotomistZoneAssignment(phlebotomist_id=p_id, zone_id=z_id)
        assert pza.phlebotomist_id == p_id
        assert pza.zone_id == z_id

    def test_assigned_at_defaults_to_none(self) -> None:
        pza = PhlebotomistZoneAssignment(
            phlebotomist_id=uuid.uuid4(), zone_id=uuid.uuid4()
        )
        assert pza.assigned_at is None

    def test_table_name(self) -> None:
        assert (
            PhlebotomistZoneAssignment.__tablename__ == "phlebotomist_zone_assignments"
        )

    def test_repr(self) -> None:
        p_id = uuid.uuid4()
        z_id = uuid.uuid4()
        pza = PhlebotomistZoneAssignment(phlebotomist_id=p_id, zone_id=z_id)
        r = repr(pza)
        assert "PhlebotomistZoneAssignment" in r
