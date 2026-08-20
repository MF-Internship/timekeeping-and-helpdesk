import pytest

from core.errors import IdentityAPIError
from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import DeleteTaskCommand
from tasks.domain.tasks import TaskStatus
from tasks.ports.authorization import TaskCreateMode
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


def service(*, creator_id: int = 42, status: TaskStatus = TaskStatus.TODO):
    repository = Repository(snapshot(creator_id=creator_id, status=status), assignees=(42,))
    audit = Audit()
    dependencies = TaskDependencies(
        Authorization(create=TaskCreateMode.SELF),
        Assignees(),
        Locations(),
        repository,
        Clock(),
        audit,
        UnitOfWork,
    )
    return TaskCommandService(dependencies), repository, audit


def test_creator_soft_deletes_self_assigned_open_task_with_audit() -> None:
    commands, repository, audit = service()

    commands.delete(DeleteTaskCommand(42, 1))

    assert repository.task is not None and repository.task.deleted_at is not None
    assert len(audit.entries) == 1


@pytest.mark.parametrize(
    ("creator_id", "status", "code"),
    [(99, TaskStatus.TODO, "NOT_FOUND"), (42, TaskStatus.COMPLETED, "TASK_ALREADY_COMPLETED")],
)
def test_delete_rejects_other_creator_and_completed_task(
    creator_id: int, status: TaskStatus, code: str
) -> None:
    commands, repository, audit = service(creator_id=creator_id, status=status)

    with pytest.raises(IdentityAPIError) as caught:
        commands.delete(DeleteTaskCommand(42, 1))

    assert caught.value.error_code == code
    assert repository.task is not None and repository.task.deleted_at is None
    assert audit.entries == []
