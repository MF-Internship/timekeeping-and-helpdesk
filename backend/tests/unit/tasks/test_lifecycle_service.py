from dataclasses import replace

import pytest

from core.errors import IdentityAPIError
from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import ChangeTaskStatusCommand, CompleteTaskOverrideCommand
from tasks.domain.tasks import CompletionMethod, TaskStatus
from tasks.ports.authorization import TaskUpdateScope
from tests.unit.tasks.fakes import (
    Assignees,
    Audit,
    Authorization,
    Clock,
    Locations,
    Repository,
    UnitOfWork,
    snapshot,
)


def build(
    source: TaskStatus,
    *,
    scope: TaskUpdateScope = TaskUpdateScope.ANY,
    actor_id: int = 10,
) -> tuple[TaskCommandService, Repository, Audit]:
    task = snapshot(creator_id=actor_id, status=source)
    repository = Repository(task, (actor_id,))
    audit = Audit()
    dependencies = TaskDependencies(
        Authorization(update=scope),
        Assignees(),
        Locations(),
        repository,
        Clock(),
        audit,
        UnitOfWork,
    )
    return TaskCommandService(dependencies), repository, audit


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (TaskStatus.TODO, TaskStatus.IN_PROGRESS),
        (TaskStatus.TODO, TaskStatus.BLOCKED),
        (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED),
        (TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS),
    ],
)
def test_allowed_nonterminal_matrix_cells_write_exactly_one_update(
    source: TaskStatus, target: TaskStatus
) -> None:
    command_service, repository, _ = build(source)
    result = command_service.change_status(
        ChangeTaskStatusCommand(
            10, 1, target, block_reason=" blocked " if target is TaskStatus.BLOCKED else None
        )
    )
    assert result.status is target
    assert len(repository.updates) == len(repository.lifecycle) == 1
    assert result.block_reason == ("blocked" if target is TaskStatus.BLOCKED else None)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (TaskStatus.IN_PROGRESS, TaskStatus.TODO),
        (TaskStatus.BLOCKED, TaskStatus.TODO),
        (TaskStatus.TODO, TaskStatus.COMPLETED),
        (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED),
        (TaskStatus.BLOCKED, TaskStatus.COMPLETED),
        (TaskStatus.COMPLETED, TaskStatus.TODO),
        (TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS),
        (TaskStatus.COMPLETED, TaskStatus.BLOCKED),
        (TaskStatus.COMPLETED, TaskStatus.COMPLETED),
    ],
)
def test_rejected_matrix_cells_have_no_side_effects(source: TaskStatus, target: TaskStatus) -> None:
    command_service, repository, _ = build(source)
    with pytest.raises(IdentityAPIError) as caught:
        command_service.change_status(ChangeTaskStatusCommand(10, 1, target))
    assert caught.value.error_code == "VALIDATION_FAILED"
    assert repository.updates == repository.lifecycle == []


@pytest.mark.parametrize("source", [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED])
def test_same_state_is_successful_noop_without_evidence(source: TaskStatus) -> None:
    command_service, repository, audit = build(source)
    before = repository.task
    assert command_service.change_status(ChangeTaskStatusCommand(10, 1, source)) == before
    assert repository.updates == repository.lifecycle == []
    assert audit.entries == audit.outbox == []


def test_blocked_accepts_note_as_reason_and_rejects_whitespace_only() -> None:
    command_service, repository, _ = build(TaskStatus.TODO)
    result = command_service.change_status(
        ChangeTaskStatusCommand(10, 1, TaskStatus.BLOCKED, note="  dependency  ")
    )
    assert result.block_reason == "dependency"
    second, second_repository, _ = build(TaskStatus.TODO)
    with pytest.raises(IdentityAPIError) as caught:
        second.change_status(ChangeTaskStatusCommand(10, 1, TaskStatus.BLOCKED, note="  "))
    assert caught.value.error_code == "BLOCK_REASON_REQUIRED"
    assert second_repository.updates == second_repository.lifecycle == []


def test_resume_clears_snapshot_reason_but_keeps_history_reason() -> None:
    command_service, repository, _ = build(TaskStatus.BLOCKED)
    result = command_service.change_status(ChangeTaskStatusCommand(10, 1, TaskStatus.IN_PROGRESS))
    assert result.block_reason is None
    assert repository.updates[0].block_reason is None


def test_override_completes_once_and_audits_without_free_text_note() -> None:
    command_service, repository, audit = build(TaskStatus.IN_PROGRESS)
    result = command_service.complete_override(
        CompleteTaskOverrideCommand(10, 1, "https://internal.invalid/incidents/1")
    )
    assert result.status is TaskStatus.COMPLETED
    assert result.completion_method is CompletionMethod.MANAGER_OVERRIDE
    assert len(repository.updates) == len(repository.lifecycle) == len(audit.entries) == 1
    assert "completion_note" not in audit.entries[0].after  # type: ignore[attr-defined]
    assert audit.outbox == []


def test_completed_is_terminal_for_status_and_override() -> None:
    command_service, repository, _ = build(TaskStatus.COMPLETED)
    repository.task = replace(
        repository.task,
        completed_by_id=10,
        completed_at=Clock().now(),
        completion_method=CompletionMethod.MANAGER_OVERRIDE,
        completion_note="done",
    )
    with pytest.raises(IdentityAPIError) as status_error:
        command_service.change_status(ChangeTaskStatusCommand(10, 1, TaskStatus.IN_PROGRESS))
    assert status_error.value.error_code == "VALIDATION_FAILED"
    with pytest.raises(IdentityAPIError) as override_error:
        command_service.complete_override(CompleteTaskOverrideCommand(10, 1, "again"))
    assert override_error.value.error_code == "TASK_ALREADY_COMPLETED"
    assert repository.updates == repository.lifecycle == []
