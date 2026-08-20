from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, transaction

from core.errors import IdentityAPIError
from identity.models import User
from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import UpdateTaskCommand
from tasks.models import TaskAssignee
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.tasks.helpers import create_task
from tests.integration.postgres.tasks.helpers import commands, production_dependencies

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_competing_full_set_replacements_are_serialized() -> None:
    manager = create_user("pg-set-manager", "MANAGER")
    retained = create_user("pg-set-retained")
    second = create_user("pg-set-second")
    third = create_user("pg-set-third")
    task = create_task(manager, retained, assigned_date=date.today())
    barrier = Barrier(2)

    def replace(extra_id: int) -> str:
        close_old_connections()
        barrier.wait()
        try:
            commands().update(
                UpdateTaskCommand(
                    manager.pk,
                    task.pk,
                    assignee_ids=(retained.pk, extra_id),
                )
            )
        except IdentityAPIError as error:
            result = error.error_code
        else:
            result = "UPDATED"
        close_old_connections()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [
            future.result()
            for future in (pool.submit(replace, second.pk), pool.submit(replace, third.pk))
        ]
    assert outcomes == ["UPDATED", "UPDATED"]
    final_ids = set(TaskAssignee.objects.filter(task=task).values_list("user_id", flat=True))
    assert final_ids in ({retained.pk, second.pk}, {retained.pk, third.pk})


@pytest.mark.parametrize("change", ["deactivate", "role"])
def test_addition_and_account_change_serialize_without_invalid_new_link(  # noqa: PLR0915
    change: str,
) -> None:
    manager = create_user(f"pg-add-{change}-manager", "MANAGER")
    retained = create_user(f"pg-add-{change}-retained")
    target = create_user(f"pg-add-{change}-target")
    task = create_task(manager, retained, assigned_date=date.today())
    barrier = Barrier(2)

    def assign() -> str:
        close_old_connections()
        barrier.wait()
        try:
            commands().update(
                UpdateTaskCommand(manager.pk, task.pk, assignee_ids=(retained.pk, target.pk))
            )
        except IdentityAPIError as error:
            result = error.error_code
        else:
            result = "UPDATED"
        close_old_connections()
        return result

    def change_account() -> None:
        close_old_connections()
        barrier.wait()
        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=target.pk)
            if change == "deactivate":
                locked.is_active = False
                locked.save(update_fields=["is_active"])
            else:
                locked.role = "LEADER"
                locked.save(update_fields=["role"])
        close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assignment = pool.submit(assign)
        account_change = pool.submit(change_account)
        outcome = assignment.result()
        account_change.result()
    assert outcome in {"UPDATED", "INACTIVE_ASSIGNEE"}
    linked = TaskAssignee.objects.filter(task=task, user=target).exists()
    assert linked is (outcome == "UPDATED")


def test_assignment_delta_rolls_back_when_later_content_write_fails() -> None:
    manager = create_user("pg-delta-rollback-manager", "MANAGER")
    current = create_user("pg-delta-rollback-current")
    added = create_user("pg-delta-rollback-added")
    task = create_task(manager, current, assigned_date=date.today())
    production = production_dependencies()

    class FailingRepository:
        def __getattr__(self, name: str) -> object:
            return getattr(production.repository, name)

        def update_content(self, record: object) -> object:
            raise RuntimeError("content write failed")

    dependencies = TaskDependencies(
        production.authorization,
        production.assignees,
        production.locations,
        FailingRepository(),  # type: ignore[arg-type]
        production.clock,
        production.audit,
        production.unit_of_work_factory,
    )
    with pytest.raises(RuntimeError, match="content write failed"):
        TaskCommandService(dependencies).update(
            UpdateTaskCommand(manager.pk, task.pk, assignee_ids=(added.pk,))
        )
    assert list(TaskAssignee.objects.filter(task=task).values_list("user_id", flat=True)) == [
        current.pk
    ]
