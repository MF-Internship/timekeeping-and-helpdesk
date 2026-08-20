from datetime import date

import pytest

from core.errors import IdentityAPIError
from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import CreateTaskCommand
from tasks.ports.authorization import TaskCreateMode
from tests.unit.tasks.fakes import (
    Assignees,
    Audit,
    Authorization,
    Clock,
    Locations,
    Repository,
    UnitOfWork,
)


def service(
    mode: TaskCreateMode,
    *,
    violating: tuple[int, ...] = (),
) -> tuple[TaskCommandService, Repository, Assignees, UnitOfWork]:
    repository = Repository()
    assignees = Assignees(violating)
    uow = UnitOfWork()
    dependencies = TaskDependencies(
        Authorization(create=mode),
        assignees,
        Locations(),
        repository,
        Clock(),
        Audit(),
        lambda: uow,
    )
    return TaskCommandService(dependencies), repository, assignees, uow


@pytest.mark.parametrize(
    "assigned_date",
    [date(2026, 8, 19), date(2026, 8, 20), date(2026, 9, 1)],
)
def test_manager_assign_normalizes_duplicates_and_keeps_supplied_date(
    assigned_date: date,
) -> None:
    command_service, repository, directory, uow = service(TaskCreateMode.ASSIGN)
    result = command_service.create(
        CreateTaskCommand(10, "  Planned work  ", "Body", assigned_date, 7, (30, 20, 30))
    )
    assert result.assigned_date == assigned_date
    assert directory.locked == [(20, 30)]
    assert repository.added[0][1] == (20, 30)
    assert repository.created[0].creator_id == 10
    assert repository.created[0].location_id == 7
    assert uow.entered == 1 and uow.exited_with is None


def test_manager_assign_requires_at_least_one_assignee() -> None:
    command_service, repository, _, _ = service(TaskCreateMode.ASSIGN)
    with pytest.raises(IdentityAPIError) as caught:
        command_service.create(CreateTaskCommand(10, "Work", "", date(2026, 8, 20)))
    assert caught.value.error_code == "VALIDATION_FAILED"
    assert repository.created == []


def test_helpdesk_self_uses_locked_actor_as_sole_assignee() -> None:
    command_service, repository, directory, _ = service(TaskCreateMode.SELF)
    result = command_service.create(CreateTaskCommand(42, "Arising", "", date(2026, 8, 19)))
    assert result.created_by_id == 42
    assert directory.self_locked == [42]
    assert repository.added[0][1] == (42,)


def test_free_expected_location_is_normalized_without_catalog_lookup() -> None:
    command_service, repository, _, _ = service(TaskCreateMode.SELF)
    command_service.create(
        CreateTaskCommand(
            42,
            "Arising",
            "",
            date(2026, 8, 19),
            expected_location="  UBND phường 1  ",
        )
    )

    assert repository.created[0].expected_location_text == "UBND phường 1"


def test_helpdesk_self_rejects_any_client_assignee_ids() -> None:
    command_service, repository, _, _ = service(TaskCreateMode.SELF)
    with pytest.raises(IdentityAPIError) as caught:
        command_service.create(
            CreateTaskCommand(42, "Arising", "", date(2026, 8, 20), assignee_ids=(42,))
        )
    assert caught.value.error_code == "SERVER_OWNED_FIELD"
    assert repository.created == []


def test_all_ineligible_ids_are_reported_sorted_and_no_task_is_created() -> None:
    command_service, repository, _, _ = service(TaskCreateMode.ASSIGN, violating=(7, 9, 11))
    with pytest.raises(IdentityAPIError) as caught:
        command_service.create(
            CreateTaskCommand(10, "Work", "", date(2026, 8, 20), assignee_ids=(11, 7, 9, 7))
        )
    assert caught.value.status_code == 422
    assert caught.value.error_code == "INACTIVE_ASSIGNEE"
    assert caught.value.details == {"assignee_ids": [7, 9, 11]}
    assert repository.created == []


def test_repository_failure_leaves_unit_of_work_with_exception() -> None:
    command_service, repository, _, uow = service(TaskCreateMode.ASSIGN)
    repository.fail_add = True
    with pytest.raises(RuntimeError, match="assignment unavailable"):
        command_service.create(
            CreateTaskCommand(10, "Work", "", date(2026, 8, 20), assignee_ids=(20,))
        )
    assert uow.exited_with is RuntimeError
