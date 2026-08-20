from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.error_codes import NOT_FOUND
from core.errors import IdentityAPIError
from tasks.application.dependencies import TaskDependencies
from tasks.domain.projections import TaskListGroup, project_task_list
from tasks.domain.tasks import TaskReadSnapshot
from tasks.ports.authorization import TaskReadScope


@dataclass(frozen=True, slots=True)
class TaskItemProjection:
    record: TaskReadSnapshot
    group: TaskListGroup
    overdue_days: int | None


@dataclass(frozen=True, slots=True)
class GroupedTaskListProjection:
    business_date: date
    overdue: tuple[TaskItemProjection, ...]
    today: tuple[TaskItemProjection, ...]
    upcoming: tuple[TaskItemProjection, ...]
    completed: tuple[TaskItemProjection, ...]


class TaskQueryService:
    def __init__(self, dependencies: TaskDependencies) -> None:
        self._dependencies = dependencies

    def list(self, actor_id: int) -> GroupedTaskListProjection:
        scope = self._dependencies.authorization.authorize_read(actor_id)
        business_date = self._dependencies.clock.business_date()
        records = self._dependencies.repository.list_detailed(
            actor_id,
            all_tasks=scope is TaskReadScope.ALL,
        )
        buckets: dict[TaskListGroup, list[TaskItemProjection]] = {
            group: [] for group in TaskListGroup
        }
        for record in records:
            projection = project_task_list(
                record.task.status,
                record.task.assigned_date,
                business_date,
            )
            buckets[projection.group].append(
                TaskItemProjection(record, projection.group, projection.overdue_days)
            )
        for values in buckets.values():
            values.sort(key=lambda item: (item.record.task.assigned_date, item.record.task.id))
        return GroupedTaskListProjection(
            business_date,
            tuple(buckets[TaskListGroup.OVERDUE]),
            tuple(buckets[TaskListGroup.TODAY]),
            tuple(buckets[TaskListGroup.UPCOMING]),
            tuple(buckets[TaskListGroup.COMPLETED]),
        )

    def detail(self, actor_id: int, task_id: int) -> TaskItemProjection:
        scope = self._dependencies.authorization.authorize_read(actor_id)
        record = self._dependencies.repository.get_detailed(
            task_id,
            actor_id,
            all_tasks=scope is TaskReadScope.ALL,
        )
        if record is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        projection = project_task_list(
            record.task.status,
            record.task.assigned_date,
            self._dependencies.clock.business_date(),
        )
        return TaskItemProjection(record, projection.group, projection.overdue_days)
