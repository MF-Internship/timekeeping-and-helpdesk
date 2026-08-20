from datetime import date

import pytest

from tasks.domain.projections import TASK_LIST_GROUP_ORDER, TaskListGroup, project_task_list
from tasks.domain.tasks import TaskStatus


@pytest.mark.unit
def test_projection_groups_are_closed_and_ordered() -> None:
    assert TASK_LIST_GROUP_ORDER == (
        TaskListGroup.OVERDUE,
        TaskListGroup.TODAY,
        TaskListGroup.UPCOMING,
        TaskListGroup.COMPLETED,
    )
    assert len(TaskListGroup) == 4


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "assigned", "expected_group", "expected_days"),
    [
        (TaskStatus.TODO, date(2026, 8, 18), TaskListGroup.OVERDUE, 2),
        (TaskStatus.BLOCKED, date(2026, 8, 20), TaskListGroup.TODAY, None),
        (TaskStatus.IN_PROGRESS, date(2026, 8, 21), TaskListGroup.UPCOMING, None),
        (TaskStatus.COMPLETED, date(2026, 8, 18), TaskListGroup.COMPLETED, None),
        (TaskStatus.COMPLETED, date(2026, 8, 21), TaskListGroup.COMPLETED, None),
    ],
)
def test_projection_is_exclusive_and_overdue_is_read_time_derived(
    status: TaskStatus,
    assigned: date,
    expected_group: TaskListGroup,
    expected_days: int | None,
) -> None:
    result = project_task_list(status, assigned, date(2026, 8, 20))
    assert result.group is expected_group
    assert result.overdue_days == expected_days
