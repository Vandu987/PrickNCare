"""Unit tests for Client and ClientUser models — task 2.2."""

import uuid

import pytest

from app.models.clients import Client, ClientUser, PaymentTerms


class TestPaymentTermsEnum:
    def test_valid_values(self) -> None:
        assert PaymentTerms.PREPAID == "prepaid"
        assert PaymentTerms.POSTPAID == "postpaid"
        assert PaymentTerms.WALLET == "wallet"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            PaymentTerms("invalid")


class TestClientModel:
    def _make_client(self, **kwargs: object) -> Client:
        defaults = {"name": "Test Lab Pvt Ltd"}
        defaults.update(kwargs)
        return Client(**defaults)  # type: ignore[arg-type]

    def test_uuid_primary_key_auto_generated(self) -> None:
        client = self._make_client()
        assert client.id is not None
        assert isinstance(uuid.UUID(str(client.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        c1 = self._make_client(name="Lab A")
        c2 = self._make_client(name="Lab B")
        assert c1.id != c2.id

    def test_is_active_defaults_to_true(self) -> None:
        client = self._make_client()
        assert client.is_active is True

    def test_payment_terms_defaults_to_prepaid(self) -> None:
        client = self._make_client()
        assert client.payment_terms == PaymentTerms.PREPAID

    def test_credit_limit_defaults_to_zero(self) -> None:
        client = self._make_client()
        assert client.credit_limit == 0

    def test_rate_fields_default_to_zero(self) -> None:
        client = self._make_client()
        assert client.rate_first_collection == 0
        assert client.rate_second_collection == 0
        assert client.rate_priority == 0

    def test_set_payment_terms(self) -> None:
        client = self._make_client(payment_terms=PaymentTerms.POSTPAID)
        assert client.payment_terms == PaymentTerms.POSTPAID

    def test_wallet_payment_terms(self) -> None:
        client = self._make_client(payment_terms=PaymentTerms.WALLET)
        assert client.payment_terms == PaymentTerms.WALLET

    def test_gst_number_optional(self) -> None:
        client = self._make_client()
        assert client.gst_number is None

    def test_gst_number_can_be_set(self) -> None:
        client = self._make_client(gst_number="27AAAAA0000A1Z5")
        assert client.gst_number == "27AAAAA0000A1Z5"

    def test_address_optional(self) -> None:
        client = self._make_client()
        assert client.address is None

    def test_created_by_optional(self) -> None:
        client = self._make_client()
        assert client.created_by is None

    def test_created_by_accepts_uuid(self) -> None:
        user_id = uuid.uuid4()
        client = self._make_client(created_by=user_id)
        assert client.created_by == user_id

    def test_table_name(self) -> None:
        assert Client.__tablename__ == "clients"

    def test_repr(self) -> None:
        client = self._make_client(name="Alpha Labs")
        r = repr(client)
        assert "Client" in r
        assert "Alpha Labs" in r
        assert "prepaid" in r

    def test_name_column_is_indexed(self) -> None:
        col = Client.__table__.c["name"]
        assert col.index is True

    def test_gst_number_column_is_unique(self) -> None:
        col = Client.__table__.c["gst_number"]
        assert col.unique is True

    def test_is_active_index_defined(self) -> None:
        index_names = {idx.name for idx in Client.__table__.indexes}
        assert "ix_clients_is_active" in index_names


class TestClientUserModel:
    def _make_client_user(self, **kwargs: object) -> ClientUser:
        defaults = {
            "client_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
        }
        defaults.update(kwargs)
        return ClientUser(**defaults)  # type: ignore[arg-type]

    def test_uuid_primary_key_auto_generated(self) -> None:
        cu = self._make_client_user()
        assert cu.id is not None
        assert isinstance(uuid.UUID(str(cu.id)), uuid.UUID)

    def test_is_primary_defaults_to_false(self) -> None:
        cu = self._make_client_user()
        assert cu.is_primary is False

    def test_is_primary_can_be_set_true(self) -> None:
        cu = self._make_client_user(is_primary=True)
        assert cu.is_primary is True

    def test_table_name(self) -> None:
        assert ClientUser.__tablename__ == "client_users"

    def test_unique_constraint_defined(self) -> None:
        constraint_names = {c.name for c in ClientUser.__table__.constraints}
        assert "uq_client_users_client_id_user_id" in constraint_names

    def test_repr(self) -> None:
        client_id = uuid.uuid4()
        user_id = uuid.uuid4()
        cu = ClientUser(client_id=client_id, user_id=user_id, is_primary=True)
        r = repr(cu)
        assert "ClientUser" in r
        assert "True" in r
