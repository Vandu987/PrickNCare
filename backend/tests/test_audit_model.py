"""Unit tests for AuditLog model — task 2.8."""

import uuid

from app.models.audit import AuditLog


def _make_audit(**kwargs: object) -> AuditLog:
    defaults = {
        "action": "create",
        "entity_type": "Order",
    }
    defaults.update(kwargs)
    return AuditLog(**defaults)  # type: ignore[arg-type]


class TestAuditLogModel:
    def test_uuid_primary_key_auto_generated(self) -> None:
        log = _make_audit()
        assert log.id is not None
        assert isinstance(uuid.UUID(str(log.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        l1 = _make_audit()
        l2 = _make_audit()
        assert l1.id != l2.id

    def test_user_id_optional(self) -> None:
        log = _make_audit()
        assert log.user_id is None

    def test_user_id_can_be_set(self) -> None:
        uid = uuid.uuid4()
        log = _make_audit(user_id=uid)
        assert log.user_id == uid

    def test_entity_id_optional(self) -> None:
        log = _make_audit()
        assert log.entity_id is None

    def test_entity_id_can_be_set(self) -> None:
        eid = uuid.uuid4()
        log = _make_audit(entity_id=eid)
        assert log.entity_id == eid

    def test_old_value_optional(self) -> None:
        log = _make_audit()
        assert log.old_value is None

    def test_new_value_optional(self) -> None:
        log = _make_audit()
        assert log.new_value is None

    def test_json_values_can_be_set(self) -> None:
        log = _make_audit(
            old_value={"status": "pending"},
            new_value={"status": "assigned"},
        )
        assert log.old_value == {"status": "pending"}
        assert log.new_value == {"status": "assigned"}

    def test_ip_address_optional(self) -> None:
        log = _make_audit()
        assert log.ip_address is None

    def test_ip_address_can_be_set(self) -> None:
        log = _make_audit(ip_address="192.168.1.100")
        assert log.ip_address == "192.168.1.100"

    def test_user_agent_optional(self) -> None:
        log = _make_audit()
        assert log.user_agent is None

    def test_action_stored(self) -> None:
        log = _make_audit(action="update")
        assert log.action == "update"

    def test_entity_type_stored(self) -> None:
        log = _make_audit(entity_type="Client")
        assert log.entity_type == "Client"

    def test_table_name(self) -> None:
        assert AuditLog.__tablename__ == "audit_logs"

    def test_entity_composite_index_defined(self) -> None:
        index_names = {idx.name for idx in AuditLog.__table__.indexes}
        assert "ix_audit_logs_entity" in index_names

    def test_user_id_index_defined(self) -> None:
        index_names = {idx.name for idx in AuditLog.__table__.indexes}
        assert "ix_audit_logs_user_id" in index_names

    def test_repr(self) -> None:
        log = _make_audit(action="delete", entity_type="Package")
        r = repr(log)
        assert "AuditLog" in r
        assert "delete" in r
        assert "Package" in r
