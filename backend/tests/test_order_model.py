"""Unit tests for Order and OrderStatusHistory models — task 2.5."""

import uuid
from datetime import date

import pytest

from app.models.orders import (
    Order,
    OrderPriority,
    OrderStatus,
    OrderStatusHistory,
    PatientGender,
    PatientTitle,
    PaymentMode,
    PaymentStatus,
)


def _make_order(**kwargs: object) -> Order:
    defaults = {
        "client_id": uuid.uuid4(),
        "pincode_id": uuid.uuid4(),
        "patient_title": PatientTitle.MR,
        "patient_name": "Rahul Sharma",
        "patient_age": 30,
        "patient_gender": PatientGender.MALE,
        "patient_phone": "+911234567890",
        "appointment_date": date(2026, 3, 1),
        "appointment_time_slot": "09:00-11:00",
        "address": "123, Test Street, Mumbai",
    }
    defaults.update(kwargs)
    return Order(**defaults)  # type: ignore[arg-type]


class TestOrderStatusEnum:
    def test_all_statuses(self) -> None:
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.ASSIGNED == "assigned"
        assert OrderStatus.ACCEPTED == "accepted"
        assert OrderStatus.IN_TRANSIT == "in_transit"
        assert OrderStatus.COLLECTED == "collected"
        assert OrderStatus.UNCOLLECTED == "uncollected"
        assert OrderStatus.CANCELLED == "cancelled"
        assert OrderStatus.NSA == "nsa"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            OrderStatus("invalid")


class TestPatientTitleEnum:
    def test_all_titles(self) -> None:
        assert PatientTitle.MR == "Mr"
        assert PatientTitle.MRS == "Mrs"
        assert PatientTitle.MS == "Ms"
        assert PatientTitle.DR == "Dr"
        assert PatientTitle.MASTER == "Master"


class TestPatientGenderEnum:
    def test_all_genders(self) -> None:
        assert PatientGender.MALE == "M"
        assert PatientGender.FEMALE == "F"
        assert PatientGender.OTHER == "O"


class TestOrderModel:
    def test_uuid_primary_key_auto_generated(self) -> None:
        order = _make_order()
        assert order.id is not None
        assert isinstance(uuid.UUID(str(order.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        o1 = _make_order()
        o2 = _make_order()
        assert o1.id != o2.id

    def test_booking_id_auto_generated(self) -> None:
        order = _make_order()
        assert order.booking_id is not None
        assert order.booking_id.startswith("BK-")

    def test_booking_id_unique_per_instance(self) -> None:
        o1 = _make_order()
        o2 = _make_order()
        assert o1.booking_id != o2.booking_id

    def test_booking_id_can_be_overridden(self) -> None:
        order = _make_order(booking_id="BK-TEST001")
        assert order.booking_id == "BK-TEST001"

    def test_status_defaults_to_pending(self) -> None:
        order = _make_order()
        assert order.status == OrderStatus.PENDING

    def test_priority_defaults_to_normal(self) -> None:
        order = _make_order()
        assert order.priority == OrderPriority.NORMAL

    def test_amount_defaults_to_zero(self) -> None:
        order = _make_order()
        assert order.amount == 0

    def test_payment_mode_defaults_to_cash(self) -> None:
        order = _make_order()
        assert order.payment_mode == PaymentMode.CASH

    def test_payment_status_defaults_to_pending(self) -> None:
        order = _make_order()
        assert order.payment_status == PaymentStatus.PENDING

    def test_locality_id_optional(self) -> None:
        order = _make_order()
        assert order.locality_id is None

    def test_assigned_phlebotomist_optional(self) -> None:
        order = _make_order()
        assert order.assigned_phlebotomist_id is None

    def test_assignment_timestamps_optional(self) -> None:
        order = _make_order()
        assert order.assigned_at is None
        assert order.accepted_at is None
        assert order.collected_at is None

    def test_proof_urls_optional(self) -> None:
        order = _make_order()
        assert order.collection_proof_url is None
        assert order.patient_signature_url is None

    def test_special_instructions_optional(self) -> None:
        order = _make_order()
        assert order.special_instructions is None

    def test_landmark_optional(self) -> None:
        order = _make_order()
        assert order.landmark is None

    def test_high_priority_order(self) -> None:
        order = _make_order(priority=OrderPriority.HIGH)
        assert order.priority == OrderPriority.HIGH

    def test_online_payment_mode(self) -> None:
        order = _make_order(payment_mode=PaymentMode.ONLINE)
        assert order.payment_mode == PaymentMode.ONLINE

    def test_table_name(self) -> None:
        assert Order.__tablename__ == "orders"

    def test_booking_id_column_is_unique(self) -> None:
        col = Order.__table__.c["booking_id"]
        assert col.unique is True

    def test_indexes_defined(self) -> None:
        index_names = {idx.name for idx in Order.__table__.indexes}
        assert "ix_orders_status_date" in index_names

    def test_repr(self) -> None:
        order = _make_order(booking_id="BK-12345678")
        r = repr(order)
        assert "Order" in r
        assert "BK-12345678" in r
        assert "pending" in r


class TestOrderStatusHistoryModel:
    def test_uuid_primary_key_auto_generated(self) -> None:
        h = OrderStatusHistory(order_id=uuid.uuid4(), status=OrderStatus.ASSIGNED)
        assert h.id is not None
        assert isinstance(uuid.UUID(str(h.id)), uuid.UUID)

    def test_notes_optional(self) -> None:
        h = OrderStatusHistory(order_id=uuid.uuid4(), status=OrderStatus.COLLECTED)
        assert h.notes is None

    def test_changed_by_optional(self) -> None:
        h = OrderStatusHistory(order_id=uuid.uuid4(), status=OrderStatus.PENDING)
        assert h.changed_by is None

    def test_table_name(self) -> None:
        assert OrderStatusHistory.__tablename__ == "order_status_history"

    def test_repr(self) -> None:
        oid = uuid.uuid4()
        h = OrderStatusHistory(order_id=oid, status=OrderStatus.ACCEPTED)
        r = repr(h)
        assert "OrderStatusHistory" in r
        assert "accepted" in r


class TestPaymentEnums:
    def test_payment_mode_values(self) -> None:
        assert PaymentMode.CASH == "cash"
        assert PaymentMode.ONLINE == "online"
        assert PaymentMode.PREPAID == "prepaid"

    def test_payment_status_values(self) -> None:
        assert PaymentStatus.PENDING == "pending"
        assert PaymentStatus.COLLECTED == "collected"
        assert PaymentStatus.VERIFIED == "verified"

    def test_order_priority_values(self) -> None:
        assert OrderPriority.NORMAL == "normal"
        assert OrderPriority.HIGH == "high"
