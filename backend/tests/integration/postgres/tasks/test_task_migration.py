import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_tasks_has_one_expand_only_leaf_and_expected_dependencies() -> None:
    loader = MigrationLoader(connection)
    assert [leaf for leaf in loader.graph.leaf_nodes() if leaf[0] == "tasks"] == [
        ("tasks", "0004_task_assignment_version")
    ]
    migration = loader.disk_migrations[("tasks", "0001_initial")]
    assert ("locations", "0001_initial") in migration.dependencies
    assert len(migration.operations) == 16


def test_task_tables_and_named_constraints_exist_after_migration() -> None:
    expected = {
        "tasks_task": {
            "task_title_nonblank",
            "task_status_valid",
            "task_block_reason_shape",
            "task_completion_shape",
            "task_status_date_id_idx",
            "task_creator_status_idx",
            "task_assignment_version_positive",
        },
        "tasks_taskassignee": {"task_assignee_unique", "task_assignee_user_idx"},
        "tasks_taskupdate": {
            "task_update_status_valid",
            "task_update_note_nonblank",
            "task_update_block_shape",
            "task_update_completion_shape",
            "task_update_task_id_idx",
        },
    }
    with connection.cursor() as cursor:
        for table, names in expected.items():
            catalog = connection.introspection.get_constraints(cursor, table)
            assert names <= set(catalog)
