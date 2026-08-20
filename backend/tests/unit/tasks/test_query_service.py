from datetime import date

from tasks.application.dependencies import TaskDependencies
from tasks.application.queries import TaskQueryService
from tasks.domain.tasks import IdentityDisplay, TaskAssigneeSnapshot, TaskReadSnapshot, TaskStatus
from tasks.ports.authorization import TaskReadScope
from tests.unit.tasks.fakes import (
    NOW,
    Assignees,
    Audit,
    Authorization,
    Clock,
    Locations,
    Repository,
    UnitOfWork,
    snapshot,
)


class CountingClock(Clock):
    def __init__(self) -> None:
        self.calls = 0

    def business_date(self) -> date:
        self.calls += 1
        return super().business_date()


class DetailedRepository(Repository):
    def __init__(self, records: tuple[TaskReadSnapshot, ...]) -> None:
        super().__init__()
        self.records = records
        self.list_arguments: list[tuple[int, bool]] = []

    def list_detailed(self, actor_id: int, *, all_tasks: bool) -> tuple[TaskReadSnapshot, ...]:
        self.list_arguments.append((actor_id, all_tasks))
        if all_tasks:
            return self.records
        return tuple(
            record
            for record in self.records
            if actor_id == record.task.created_by_id
            or actor_id in {assignee.user.id for assignee in record.assignees}
        )


def record(task_id: int, assigned: date, status: TaskStatus, creator: int = 10) -> TaskReadSnapshot:
    task = snapshot(task_id=task_id, creator_id=creator, status=status, assigned_date=assigned)
    return TaskReadSnapshot(
        task,
        IdentityDisplay(creator, "Creator"),
        None,
        (TaskAssigneeSnapshot(IdentityDisplay(10, "Historical Assignee"), NOW),),
        None,
        (),
    )


def test_list_captures_one_business_date_and_assigns_each_record_once() -> None:
    clock = CountingClock()
    repository = DetailedRepository(
        (
            record(1, date(2026, 8, 18), TaskStatus.TODO),
            record(2, date(2026, 8, 20), TaskStatus.BLOCKED),
            record(3, date(2026, 8, 21), TaskStatus.IN_PROGRESS),
            record(4, date(2026, 1, 1), TaskStatus.COMPLETED),
        )
    )
    dependencies = TaskDependencies(
        Authorization(read=TaskReadScope.SELF),
        Assignees(),
        Locations(),
        repository,
        clock,
        Audit(),
        UnitOfWork,
    )
    result = TaskQueryService(dependencies).list(10)
    groups = (result.overdue, result.today, result.upcoming, result.completed)
    assert [[item.record.task.id for item in group] for group in groups] == [[1], [2], [3], [4]]
    assert result.overdue[0].overdue_days == 2
    assert result.completed[0].overdue_days is None
    assert result.overdue[0].record.assignees[0].user.full_name == "Historical Assignee"
    assert clock.calls == 1
    assert repository.list_arguments == [(10, False)]


def test_all_scope_uses_repository_bypass_but_keeps_projection_rules() -> None:
    repository = DetailedRepository((record(9, date(2026, 8, 20), TaskStatus.TODO, 99),))
    dependencies = TaskDependencies(
        Authorization(read=TaskReadScope.ALL),
        Assignees(),
        Locations(),
        repository,
        Clock(),
        Audit(),
        UnitOfWork,
    )
    result = TaskQueryService(dependencies).list(10)
    assert result.today[0].record.task.id == 9
    assert repository.list_arguments == [(10, True)]
