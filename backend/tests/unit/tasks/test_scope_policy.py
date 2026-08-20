import pytest

from core.errors import IdentityAPIError
from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import ChangeTaskStatusCommand
from tasks.domain.tasks import TaskStatus
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


def command_service(
    actor_id: int, creator_id: int, assignees: tuple[int, ...], scope: TaskUpdateScope
) -> tuple[TaskCommandService, Repository]:
    repository = Repository(snapshot(creator_id=creator_id), assignees)
    dependencies = TaskDependencies(
        Authorization(update=scope),
        Assignees(),
        Locations(),
        repository,
        Clock(),
        Audit(),
        UnitOfWork,
    )
    return TaskCommandService(dependencies), repository


@pytest.mark.parametrize(("creator", "assignees"), [(10, (20,)), (20, (10,))])
def test_self_scope_is_creator_or_assignee(creator: int, assignees: tuple[int, ...]) -> None:
    service, repository = command_service(10, creator, assignees, TaskUpdateScope.SELF)
    assert (
        service.change_status(ChangeTaskStatusCommand(10, 1, TaskStatus.IN_PROGRESS)).status
        is TaskStatus.IN_PROGRESS
    )
    assert len(repository.updates) == 1


def test_unrelated_self_scope_is_scope_safe_not_found() -> None:
    service, repository = command_service(10, 20, (30,), TaskUpdateScope.SELF)
    with pytest.raises(IdentityAPIError) as caught:
        service.change_status(ChangeTaskStatusCommand(10, 1, TaskStatus.IN_PROGRESS))
    assert caught.value.error_code == "NOT_FOUND"
    assert repository.updates == []


def test_any_scope_does_not_bypass_invalid_transition() -> None:
    service, repository = command_service(10, 20, (30,), TaskUpdateScope.ANY)
    repository.task = snapshot(creator_id=20, status=TaskStatus.IN_PROGRESS)
    with pytest.raises(IdentityAPIError) as caught:
        service.change_status(ChangeTaskStatusCommand(10, 1, TaskStatus.TODO))
    assert caught.value.error_code == "VALIDATION_FAILED"
    assert repository.updates == []
