from datetime import date

from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import (
    CompleteTaskOverrideCommand,
    CreateTaskCommand,
    UpdateTaskCommand,
)
from tasks.domain.tasks import TaskStatus
from tasks.ports.authorization import TaskCreateMode
from tests.unit.tasks.fakes import (
    Assignees,
    Audit,
    Authorization,
    Clock,
    Locations,
    Notifications,
    Repository,
    UnitOfWork,
    snapshot,
)


def _service(repository: Repository, notifications: Notifications) -> TaskCommandService:
    return TaskCommandService(
        TaskDependencies(
            Authorization(create=TaskCreateMode.ASSIGN),
            Assignees(),
            Locations(),
            repository,
            Clock(),
            Audit(),
            UnitOfWork,
            notifications=notifications,
        )
    )


def test_create_records_added_assignees_at_initial_assignment_version() -> None:
    notifications = Notifications()
    service = _service(Repository(), notifications)

    service.create(CreateTaskCommand(10, "Task", "", date(2026, 8, 21), assignee_ids=(22, 21)))

    assert notifications.assignments == [(99, (21, 22), 1)]


def test_real_assignment_delta_increments_once_and_noop_does_not_emit() -> None:
    repository = Repository(snapshot(), (20, 21))
    notifications = Notifications()
    service = _service(repository, notifications)

    service.update(UpdateTaskCommand(10, 1, assignee_ids=(20, 22)))
    assert repository.task is not None and repository.task.assignment_version == 2
    assert notifications.removed == [(1, (21,))]
    assert notifications.assignments == [(1, (22,), 2)]

    service.update(UpdateTaskCommand(10, 1, title="Changed", assignee_ids=(20, 22)))
    assert repository.task.assignment_version == 2
    assert len(notifications.assignments) == 1


def test_manager_override_suppresses_reminders_without_event_five() -> None:
    repository = Repository(snapshot(status=TaskStatus.IN_PROGRESS), (10, 20))
    notifications = Notifications()

    _service(repository, notifications).complete_override(
        CompleteTaskOverrideCommand(10, 1, "approved incident")
    )

    assert notifications.suppressed_tasks == [1]
    assert notifications.completions == []
