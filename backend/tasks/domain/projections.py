from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from tasks.domain.tasks import TaskStatus


class TaskListGroup(StrEnum):
    OVERDUE = "OVERDUE"
    TODAY = "TODAY"
    UPCOMING = "UPCOMING"
    COMPLETED = "COMPLETED"


TASK_LIST_GROUP_ORDER = (
    TaskListGroup.OVERDUE,
    TaskListGroup.TODAY,
    TaskListGroup.UPCOMING,
    TaskListGroup.COMPLETED,
)


@dataclass(frozen=True, slots=True)
class TaskListProjection:
    group: TaskListGroup
    overdue_days: int | None


def project_task_list(
    status: TaskStatus, assigned_date: date, business_date: date
) -> TaskListProjection:
    if status is TaskStatus.COMPLETED:
        return TaskListProjection(TaskListGroup.COMPLETED, None)
    difference = (business_date - assigned_date).days
    if difference > 0:
        return TaskListProjection(TaskListGroup.OVERDUE, difference)
    if difference == 0:
        return TaskListProjection(TaskListGroup.TODAY, None)
    return TaskListProjection(TaskListGroup.UPCOMING, None)
