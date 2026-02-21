"""Unit tests for geographic hierarchy models — task 2.4."""

import uuid

from app.models.zones import City, Locality, Pincode, Zone


class TestCityModel:
    def _make_city(self, **kwargs: object) -> City:
        defaults = {"name": "Mumbai", "state": "Maharashtra"}
        defaults.update(kwargs)
        return City(**defaults)  # type: ignore[arg-type]

    def test_uuid_primary_key_auto_generated(self) -> None:
        city = self._make_city()
        assert city.id is not None
        assert isinstance(uuid.UUID(str(city.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        c1 = self._make_city(name="Mumbai")
        c2 = self._make_city(name="Delhi")
        assert c1.id != c2.id

    def test_is_serviceable_defaults_to_true(self) -> None:
        city = self._make_city()
        assert city.is_serviceable is True

    def test_is_serviceable_can_be_set_false(self) -> None:
        city = self._make_city(is_serviceable=False)
        assert city.is_serviceable is False

    def test_table_name(self) -> None:
        assert City.__tablename__ == "cities"

    def test_name_column_is_indexed(self) -> None:
        col = City.__table__.c["name"]
        assert col.index is True

    def test_is_serviceable_index_defined(self) -> None:
        index_names = {idx.name for idx in City.__table__.indexes}
        assert "ix_cities_is_serviceable" in index_names

    def test_repr(self) -> None:
        city = self._make_city(name="Pune", state="Maharashtra")
        r = repr(city)
        assert "City" in r
        assert "Pune" in r
        assert "Maharashtra" in r


class TestZoneModel:
    def _make_zone(self, **kwargs: object) -> Zone:
        defaults = {"city_id": uuid.uuid4(), "name": "Zone A"}
        defaults.update(kwargs)
        return Zone(**defaults)  # type: ignore[arg-type]

    def test_uuid_primary_key_auto_generated(self) -> None:
        zone = self._make_zone()
        assert zone.id is not None
        assert isinstance(uuid.UUID(str(zone.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        z1 = self._make_zone(name="North")
        z2 = self._make_zone(name="South")
        assert z1.id != z2.id

    def test_is_active_defaults_to_true(self) -> None:
        zone = self._make_zone()
        assert zone.is_active is True

    def test_is_active_can_be_set_false(self) -> None:
        zone = self._make_zone(is_active=False)
        assert zone.is_active is False

    def test_table_name(self) -> None:
        assert Zone.__tablename__ == "zones"

    def test_unique_constraint_city_name(self) -> None:
        constraint_names = {c.name for c in Zone.__table__.constraints}
        assert "uq_zones_city_id_name" in constraint_names

    def test_is_active_index_defined(self) -> None:
        index_names = {idx.name for idx in Zone.__table__.indexes}
        assert "ix_zones_is_active" in index_names

    def test_repr(self) -> None:
        city_id = uuid.uuid4()
        zone = self._make_zone(city_id=city_id, name="East Zone")
        r = repr(zone)
        assert "Zone" in r
        assert "East Zone" in r


class TestPincodeModel:
    def _make_pincode(self, **kwargs: object) -> Pincode:
        defaults = {"zone_id": uuid.uuid4(), "pincode": "400001"}
        defaults.update(kwargs)
        return Pincode(**defaults)  # type: ignore[arg-type]

    def test_uuid_primary_key_auto_generated(self) -> None:
        p = self._make_pincode()
        assert p.id is not None
        assert isinstance(uuid.UUID(str(p.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        p1 = self._make_pincode(pincode="400001")
        p2 = self._make_pincode(pincode="400002")
        assert p1.id != p2.id

    def test_table_name(self) -> None:
        assert Pincode.__tablename__ == "pincodes"

    def test_pincode_column_is_unique_and_indexed(self) -> None:
        col = Pincode.__table__.c["pincode"]
        assert col.unique is True
        assert col.index is True

    def test_repr(self) -> None:
        p = self._make_pincode(pincode="110001")
        r = repr(p)
        assert "Pincode" in r
        assert "110001" in r


class TestLocalityModel:
    def _make_locality(self, **kwargs: object) -> Locality:
        defaults = {"pincode_id": uuid.uuid4(), "name": "Andheri West"}
        defaults.update(kwargs)
        return Locality(**defaults)  # type: ignore[arg-type]

    def test_uuid_primary_key_auto_generated(self) -> None:
        loc = self._make_locality()
        assert loc.id is not None
        assert isinstance(uuid.UUID(str(loc.id)), uuid.UUID)

    def test_uuid_unique_per_instance(self) -> None:
        l1 = self._make_locality(name="Bandra")
        l2 = self._make_locality(name="Kurla")
        assert l1.id != l2.id

    def test_table_name(self) -> None:
        assert Locality.__tablename__ == "localities"

    def test_unique_constraint_pincode_name(self) -> None:
        constraint_names = {c.name for c in Locality.__table__.constraints}
        assert "uq_localities_pincode_id_name" in constraint_names

    def test_repr(self) -> None:
        loc = self._make_locality(name="Dadar")
        r = repr(loc)
        assert "Locality" in r
        assert "Dadar" in r
