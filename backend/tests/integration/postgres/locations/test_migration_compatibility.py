from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_locations_has_one_additive_leaf_and_immutable_code_trigger() -> None:
    loader = MigrationLoader(connection)
    assert [leaf for leaf in loader.graph.leaf_nodes() if leaf[0] == "locations"] == [
        ("locations", "0001_initial")
    ]
    assert loader.disk_migrations[("locations", "0001_initial")].dependencies == []
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM pg_trigger WHERE tgname = 'locations_code_immutable'")
        assert cursor.fetchone() == (1,)
