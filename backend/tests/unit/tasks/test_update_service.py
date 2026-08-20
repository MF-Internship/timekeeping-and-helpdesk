from dataclasses import replace

import pytest

from core.errors import IdentityAPIError
from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import UpdateTaskCommand
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
    *,
    scope: TaskUpdateScope = TaskUpdateScope.ANY,
    violating: tuple[int, ...] = (),
    current: tuple[int, ...] = (20, 21),
) -> tuple[TaskCommandService, Repository, Assignees]:
    repository = Repository(snapshot(), current)
    assignees = Assignees(violating)
    dependencies = TaskDependencies(
        Authorization(update=scope),
        assignees,
        Locations(),
        repository,
        Clock(),
        Audit(),
        UnitOfWork,
    )
    return TaskCommandService(dependencies), repository, assignees


def test_any_scope_full_set_validates_additions_only_and_retains_inactive_history() -> None:
    command_service, repository, directory = build()
    result = command_service.update(
        UpdateTaskCommand(10, 1, title="Edited", assignee_ids=(20, 22, 22))
    )
    assert result.assigned_date == repository.task.assigned_date
    assert directory.locked == [(22,)]
    assert repository.replacements == [((21,), (22,))]


def test_empty_desired_set_is_rejected_without_delta() -> None:
    command_service, repository, _ = build()
    with pytest.raises(IdentityAPIError) as caught:
        command_service.update(UpdateTaskCommand(10, 1, assignee_ids=()))
    assert caught.value.error_code == "VALIDATION_FAILED"
    assert repository.replacements == []


def test_expected_location_can_be_cleared_without_changing_assigned_date() -> None:
    command_service, repository, _ = build()
    repository.task = replace(repository.task, location_id=7)
    assigned_date = repository.task.assigned_date
    result = command_service.update(
        UpdateTaskCommand(10, 1, location_id=None, replace_location=True)
    )
    assert result.location_id is None
    assert result.assigned_date == assigned_date


def test_self_scope_cannot_manage_assignees_even_in_object_scope() -> None:
    command_service, repository, _ = build(scope=TaskUpdateScope.SELF, current=(10,))
    with pytest.raises(IdentityAPIError) as caught:
        command_service.update(UpdateTaskCommand(10, 1, assignee_ids=(10, 20)))
    assert caught.value.error_code in {"PERMISSION_DENIED", "SERVER_OWNED_FIELD"}
    assert repository.replacements == []


def test_readding_removed_inactive_user_is_a_new_ineligible_assignment() -> None:
    command_service, repository, _ = build(violating=(21,), current=(20,))
    with pytest.raises(IdentityAPIError) as caught:
        command_service.update(UpdateTaskCommand(10, 1, assignee_ids=(20, 21)))
    assert caught.value.error_code == "INACTIVE_ASSIGNEE"
    assert caught.value.details == {"assignee_ids": [21]}
    assert repository.replacements == []


def test_completed_task_rejects_content_location_and_assignee_changes() -> None:
    command_service, repository, _ = build()
    repository.task = replace(
        repository.task,
        status=TaskStatus.COMPLETED,
        completed_by_id=10,
        completed_at=Clock().now(),
        completion_method=CompletionMethod.MANAGER_OVERRIDE,
        completion_note="done",
    )
    with pytest.raises(IdentityAPIError):
        command_service.update(
            UpdateTaskCommand(
                10, 1, title="No", location_id=2, replace_location=True, assignee_ids=(20,)
            )
        )
    assert repository.replacements == []
