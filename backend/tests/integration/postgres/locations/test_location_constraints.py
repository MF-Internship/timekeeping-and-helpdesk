from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction

from locations.models import Location


def location(code: str, **overrides: object) -> Location:
    values: dict[str, object] = {
        "code": code,
        "name": code,
        "kind": "SHOP",
        "address": "Address",
        "latitude": Decimal("10.123456789012345"),
        "longitude": Decimal("106.123456789012345"),
        "radius_m": Decimal("50.000"),
    }
    values.update(overrides)
    return Location.objects.create(**values)


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_location_constraints_and_duplicate_coordinates() -> None:
    first = location("A")
    second = location("B")
    first.refresh_from_db()
    assert first.latitude == Decimal("10.123456789012345")
    assert first.latitude == second.latitude
    assert first.longitude == second.longitude
    for code, overrides in (
        ("A", {}),
        ("   ", {}),
        ("blank", {"name": "   "}),
        ("blank-address", {"address": "   "}),
        ("bad-kind", {"kind": "OFFICE"}),
        ("bad-lat", {"latitude": Decimal("91")}),
        ("bad-lng", {"longitude": Decimal("181")}),
        ("bad-radius", {"radius_m": Decimal("0")}),
        ("bad-version", {"version": 0}),
    ):
        with pytest.raises((IntegrityError, DatabaseError)), transaction.atomic():
            location(code, **overrides)
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, Location._meta.db_table)
    assert constraints["location_kind_code_idx"]["index"] is True
    assert constraints["location_parent_idx"]["index"] is True
    assert constraints["location_active_idx"]["index"] is True


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_code_is_immutable_and_parent_is_protected() -> None:
    parent = location("CENTER", kind="BUSINESS_CENTER")
    child = location("SHOP", parent=parent)
    child.code = "CHANGED"
    with pytest.raises(DatabaseError), transaction.atomic():
        child.save(update_fields=["code"])
    with pytest.raises(IntegrityError), transaction.atomic():
        parent.delete()


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_is_active_is_not_null_and_has_a_database_default() -> None:
    table = connection.ops.quote_name(Location._meta.db_table)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""INSERT INTO {table}
                (code, name, kind, address, latitude, longitude, radius_m)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING is_active, version""",
            ["DDL-DEFAULT", "DDL Default", "SHOP", "Address", 10, 106, 50],
        )
        assert cursor.fetchone() == (True, 1)

    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            f"""INSERT INTO {table}
                (code, name, kind, address, latitude, longitude, radius_m, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)""",
            ["NULL-ACTIVE", "Null Active", "SHOP", "Address", 10, 106, 50],
        )
