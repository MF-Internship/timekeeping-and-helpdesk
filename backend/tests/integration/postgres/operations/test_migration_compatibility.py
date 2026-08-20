from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_job_run_migration_is_additive_empty_and_single_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("operations", "0001_throttle_cache_table")])
    before = set(connection.introspection.table_names())
    assert "operations_jobrun" not in before

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    after = set(connection.introspection.table_names())
    assert before <= after
    assert "operations_jobrun" in after
    assert "operations_jobheartbeat" in after

    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM operations_jobrun")
        assert cursor.fetchone() == (0,)
        cursor.execute("SELECT COUNT(*) FROM operations_jobheartbeat")
        assert cursor.fetchone() == (0,)
    leaves = MigrationExecutor(connection).loader.graph.leaf_nodes("operations")
    assert leaves == [("operations", "0003_observability")]
