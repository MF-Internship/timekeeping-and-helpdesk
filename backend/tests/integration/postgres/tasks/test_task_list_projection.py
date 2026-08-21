from datetime import date, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from tasks.application.dependencies import TaskDependencies
from tasks.application.queries import TaskQueryService
from tasks.models import Task, TaskAssignee
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.tasks.helpers import create_task
from tests.integration.postgres.tasks.helpers import production_dependencies, queries

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_representative_list_uses_bounded_queries_and_scope_index() -> None:
    manager = create_user("pg-list-manager", "MANAGER")
    assignees = [create_user(f"pg-list-assignee-{index}") for index in range(5)]
    today = date.today()
    for index in range(60):
        create_task(
            manager,
            assignees[index % len(assignees)],
            assigned_date=today + timedelta(days=(index % 7) - 3),
            title=f"Task {index}",
        )
    with CaptureQueriesContext(connection) as captured:
        result = queries().list(manager.pk)
    assert sum(len(group) for group in (result.overdue, result.today, result.upcoming)) == 60
    # Two Identity authorization/account-gate queries plus one Task query and
    # two bounded prefetches; the count must not grow with the result size.
    assert len(captured) <= 5
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")
        cursor.execute(
            "EXPLAIN SELECT id FROM tasks_task WHERE status = %s ORDER BY assigned_date, id",
            ["TODO"],
        )
        plan = "\n".join(row[0] for row in cursor.fetchall())
    assert "task_status_date_id_idx" in plan


def test_business_date_is_captured_once_and_read_does_not_mutate_rows() -> None:
    manager = create_user("pg-midnight-manager", "MANAGER")
    assignee = create_user("pg-midnight-assignee")
    task = create_task(manager, assignee, assigned_date=date(2026, 8, 20))
    production = production_dependencies()

    class MidnightClock:
        calls = 0

        def now(self) -> object:
            return production.clock.now()

        def business_date(self) -> date:
            self.calls += 1
            return date(2026, 8, 20) if self.calls == 1 else date(2026, 8, 21)

    clock = MidnightClock()
    dependencies = TaskDependencies(
        production.authorization,
        production.assignees,
        production.locations,
        production.repository,
        clock,  # type: ignore[arg-type]
        production.audit,
        production.unit_of_work_factory,
    )
    before = Task.objects.values_list("assigned_date", "status").get(pk=task.pk)
    result = TaskQueryService(dependencies).list(manager.pk)
    assert clock.calls == 1
    assert [item.record.task.id for item in result.today] == [task.pk]
    assert Task.objects.values_list("assigned_date", "status").get(pk=task.pk) == before


def test_helpdesk_soft_delete_retains_rows_and_filters_repository_reads() -> None:
    actor = create_user("pg-delete-helpdesk", "HELPDESK")
    task = create_task(actor, actor, assigned_date=date.today())
    repository = production_dependencies().repository

    repository.soft_delete(task.pk, timezone.now())

    retained = Task.objects.get(pk=task.pk)
    assert retained.deleted_at is not None
    assert TaskAssignee.objects.filter(task_id=task.pk, user_id=actor.pk).exists()
    assert repository.get(task.pk) is None
    assert all(item.id != task.pk for item in repository.list_scoped(actor.pk, all_tasks=False))
