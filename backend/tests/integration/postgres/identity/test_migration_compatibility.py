from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_feature_002_is_additive_and_auth_foreign_keys_use_custom_user() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(
        [
            ("operations", "0001_throttle_cache_table"),
            ("audit", None),
            ("token_blacklist", None),
            ("auth", None),
            ("contenttypes", None),
            ("identity", None),
        ]
    )
    assert "throttle_cache" in connection.introspection.table_names()
    assert "identity_user" not in connection.introspection.table_names()

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    executor = MigrationExecutor(connection)
    leaves = set(executor.loader.graph.leaf_nodes())
    assert len([leaf for leaf in leaves if leaf[0] == "operations"]) == 1
    assert len([leaf for leaf in leaves if leaf[0] == "identity"]) == 1
    assert len([leaf for leaf in leaves if leaf[0] == "audit"]) == 1

    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "audit_auditlog")
        audit_fk = [value["foreign_key"] for value in constraints.values() if value["foreign_key"]]
        token_constraints = connection.introspection.get_constraints(
            cursor, "token_blacklist_outstandingtoken"
        )
        token_fks = [
            value["foreign_key"] for value in token_constraints.values() if value["foreign_key"]
        ]
    assert ("identity_user", "id") in audit_fk
    assert ("identity_user", "id") in token_fks
