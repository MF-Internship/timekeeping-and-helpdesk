import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_attendance_has_one_additive_initial_leaf() -> None:
    loader = MigrationLoader(connection)
    assert [leaf for leaf in loader.graph.leaf_nodes() if leaf[0] == "attendance"] == [
        ("attendance", "0001_initial")
    ]
    migration = loader.disk_migrations[("attendance", "0001_initial")]
    assert set(migration.dependencies) == {
        ("identity", "__first__"),
        ("locations", "0001_initial"),
    }
    assert all(
        operation.__class__.__name__ not in {"RunPython", "RunSQL"}
        for operation in migration.operations
    )
