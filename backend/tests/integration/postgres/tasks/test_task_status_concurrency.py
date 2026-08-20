from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections

from audit.models import AuditLog, OutboxEvent
from core.errors import IdentityAPIError
from tasks.application.dto import (
    ChangeTaskStatusCommand,
    CompleteTaskOverrideCommand,
    UpdateTaskCommand,
)
from tasks.domain.tasks import TaskStatus
from tasks.models import TaskUpdate
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.tasks.helpers import create_task
from tests.integration.postgres.tasks.helpers import commands

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def race(first: Callable[[], str], second: Callable[[], str]) -> list[str]:
    barrier = Barrier(2)

    def run(operation: Callable[[], str]) -> str:
        close_old_connections()
        barrier.wait()
        try:
            result = operation()
        except IdentityAPIError as error:
            result = error.error_code
        close_old_connections()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        return [future.result() for future in (pool.submit(run, first), pool.submit(run, second))]


def test_valid_chained_status_transitions_serialize_and_both_commit() -> None:
    manager = create_user("pg-status-chain-manager", "MANAGER")
    assignee = create_user("pg-status-chain-assignee")
    task = create_task(manager, assignee, assigned_date=date.today())
    outcomes = race(
        lambda: commands()
        .change_status(ChangeTaskStatusCommand(manager.pk, task.pk, TaskStatus.IN_PROGRESS))
        .status.value,
        lambda: commands()
        .change_status(
            ChangeTaskStatusCommand(manager.pk, task.pk, TaskStatus.BLOCKED, block_reason="blocked")
        )
        .status.value,
    )
    task.refresh_from_db()
    assert set(outcomes) == {"IN_PROGRESS", "BLOCKED"}
    assert TaskUpdate.objects.filter(task=task).count() == 2
    assert task.status in {"IN_PROGRESS", "BLOCKED"}


def test_duplicate_same_target_has_one_transition_and_one_noop() -> None:
    manager = create_user("pg-status-noop-manager", "MANAGER")
    assignee = create_user("pg-status-noop-assignee")
    task = create_task(manager, assignee, assigned_date=date.today())

    def operation() -> str:
        return (
            commands()
            .change_status(ChangeTaskStatusCommand(manager.pk, task.pk, TaskStatus.IN_PROGRESS))
            .status.value
        )

    assert race(operation, operation) == ["IN_PROGRESS", "IN_PROGRESS"]
    assert TaskUpdate.objects.filter(task=task).count() == 1
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


def test_later_invalid_edge_is_rejected_without_losing_winner_delta() -> None:
    manager = create_user("pg-status-invalid-manager", "MANAGER")
    assignee = create_user("pg-status-invalid-assignee")
    task = create_task(
        manager,
        assignee,
        assigned_date=date.today(),
        status="IN_PROGRESS",
    )
    outcomes = race(
        lambda: commands()
        .change_status(
            ChangeTaskStatusCommand(manager.pk, task.pk, TaskStatus.BLOCKED, block_reason="blocked")
        )
        .status.value,
        lambda: commands()
        .change_status(ChangeTaskStatusCommand(manager.pk, task.pk, TaskStatus.TODO))
        .status.value,
    )
    assert set(outcomes) == {"BLOCKED", "VALIDATION_FAILED"}
    assert TaskUpdate.objects.filter(task=task, status="BLOCKED").count() == 1


def test_status_and_override_race_finishes_once_without_losing_deltas() -> None:
    manager = create_user("pg-status-override-manager", "MANAGER")
    assignee = create_user("pg-status-override-assignee")
    task = create_task(manager, assignee, assigned_date=date.today())
    outcomes = race(
        lambda: commands()
        .change_status(ChangeTaskStatusCommand(manager.pk, task.pk, TaskStatus.IN_PROGRESS))
        .status.value,
        lambda: commands()
        .complete_override(CompleteTaskOverrideCommand(manager.pk, task.pk, "complete"))
        .status.value,
    )
    task.refresh_from_db()
    assert task.status == "COMPLETED" and "COMPLETED" in outcomes
    assert len(outcomes) == 2
    assert TaskUpdate.objects.filter(task=task, status="COMPLETED").count() == 1
    assert AuditLog.objects.filter(target_type="Task", target_id=str(task.pk)).count() == 1


def test_metadata_update_and_override_serialize_with_completed_freeze() -> None:
    manager = create_user("pg-content-override-manager", "MANAGER")
    assignee = create_user("pg-content-override-assignee")
    task = create_task(manager, assignee, assigned_date=date.today())
    outcomes = race(
        lambda: commands().update(UpdateTaskCommand(manager.pk, task.pk, title="Edited")).title,
        lambda: commands()
        .complete_override(CompleteTaskOverrideCommand(manager.pk, task.pk, "complete"))
        .status.value,
    )
    task.refresh_from_db()
    assert task.status == "COMPLETED"
    assert outcomes[0] in {"Edited", "VALIDATION_FAILED"}
    assert outcomes[1] == "COMPLETED"
    assert TaskUpdate.objects.filter(task=task, status="COMPLETED").count() == 1
    assert AuditLog.objects.filter(target_type="Task", target_id=str(task.pk)).count() == 1


def test_duplicate_override_has_exactly_one_completion_and_audit() -> None:
    manager = create_user("pg-duplicate-override-manager", "MANAGER")
    assignee = create_user("pg-duplicate-override-assignee")
    task = create_task(manager, assignee, assigned_date=date.today())

    def complete() -> str:
        return (
            commands()
            .complete_override(CompleteTaskOverrideCommand(manager.pk, task.pk, "complete"))
            .status.value
        )

    assert set(race(complete, complete)) == {"COMPLETED", "TASK_ALREADY_COMPLETED"}
    assert TaskUpdate.objects.filter(task=task, status="COMPLETED").count() == 1
    assert AuditLog.objects.filter(target_type="Task", target_id=str(task.pk)).count() == 1
    assert not OutboxEvent.objects.exists()
