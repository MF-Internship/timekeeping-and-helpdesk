from datetime import UTC, date, datetime

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction

from identity.domain.authorization import Role
from identity.models import User
from tasks.models import Task, TaskAssignee, TaskUpdate

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def user(username: str) -> User:
    return User.objects.create_user(
        username=username,
        password="test-password",
        full_name=username,
        role=Role.HELPDESK.value,
        must_change_password=False,
    )


def task(creator: User, **overrides: object) -> Task:
    values: dict[str, object] = {
        "title": "Task",
        "created_by": creator,
        "assigned_date": date(2026, 8, 20),
    }
    values.update(overrides)
    return Task.objects.create(**values)


@pytest.mark.parametrize(
    "invalid_update",
    (
        {"status": "BLOCKED"},
        {"status": "TODO", "block_reason": "reason"},
        {"status": "TODO", "note": "  "},
        {"status": "COMPLETED"},
        {"status": "IN_PROGRESS", "completion_method": "MANAGER_OVERRIDE"},
    ),
)
def test_task_and_update_snapshot_constraints_reject_invalid_rows(
    invalid_update: dict[str, object],
) -> None:
    creator = user("task-constraint-creator")
    valid = task(creator)
    invalid_tasks = (
        {"title": "   "},
        {"status": "UNKNOWN"},
        {"status": "BLOCKED", "block_reason": None},
        {"status": "TODO", "block_reason": "reason"},
        {"status": "COMPLETED"},
        {"status": "TODO", "completion_method": "MANAGER_OVERRIDE"},
    )
    for values in invalid_tasks:
        with pytest.raises((IntegrityError, DatabaseError)), transaction.atomic():
            task(creator, **values)
    with pytest.raises((IntegrityError, DatabaseError)), transaction.atomic():
        TaskUpdate.objects.create(task=valid, user=creator, **invalid_update)
    TaskUpdate.objects.create(
        task=valid,
        user=creator,
        status="COMPLETED",
        completion_method="MANAGER_OVERRIDE",
        completion_note="done",
    )


def test_assignee_uniqueness_and_protect_foreign_keys() -> None:
    creator = user("task-assignee-creator")
    assignee = user("task-assignee-user")
    model = task(creator)
    TaskAssignee.objects.create(task=model, user=assignee)
    with pytest.raises(IntegrityError), transaction.atomic():
        TaskAssignee.objects.create(task=model, user=assignee)
    with pytest.raises(IntegrityError), transaction.atomic():
        model.delete()
    with pytest.raises(IntegrityError), transaction.atomic():
        assignee.delete()


def test_database_defaults_and_required_indexes_are_in_catalog() -> None:
    creator = user("task-default-creator")
    table = connection.ops.quote_name(Task._meta.db_table)
    with connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {table} (title, description, created_by_id, assigned_date) "
            "VALUES (%s, %s, %s, %s) RETURNING status",
            ["DDL default", "", creator.pk, date(2026, 8, 20)],
        )
        assert cursor.fetchone() == ("TODO",)
        task_constraints = connection.introspection.get_constraints(cursor, Task._meta.db_table)
        assignee_constraints = connection.introspection.get_constraints(
            cursor, TaskAssignee._meta.db_table
        )
        update_constraints = connection.introspection.get_constraints(
            cursor, TaskUpdate._meta.db_table
        )
    assert task_constraints["task_status_date_id_idx"]["index"] is True
    assert task_constraints["task_creator_status_idx"]["index"] is True
    assert assignee_constraints["task_assignee_unique"]["unique"] is True
    assert assignee_constraints["task_assignee_user_idx"]["index"] is True
    assert update_constraints["task_update_task_id_idx"]["index"] is True


def test_valid_completed_snapshot_is_accepted() -> None:
    creator = user("task-complete-creator")
    model = task(
        creator,
        status="COMPLETED",
        completed_by=creator,
        completed_at=datetime(2026, 8, 20, tzinfo=UTC),
        completion_method="MANAGER_OVERRIDE",
        completion_note="done",
    )
    assert model.pk
