from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from notifications.application.dispatch import OccurrenceDispatcher
from notifications.application.dto import AttendanceCandidate, TaskCandidate
from notifications.domain.events import NotificationEventType

NOW = datetime(2026, 8, 21, 3, tzinfo=UTC)


@pytest.mark.unit
def test_dispatch_records_only_current_task_and_open_attendance_candidates() -> None:
    recorded: list[object] = []
    tasks = SimpleNamespace(
        due_upcoming=lambda now: (
            TaskCandidate(10, (1, 2), date(2026, 8, 22), 1, False),
            TaskCandidate(11, (1,), date(2026, 8, 22), 1, True),
        ),
        due_overdue=lambda now: (),
        revalidate=lambda task_id, recipient_id, event: recipient_id == 1,
    )
    attendance = SimpleNamespace(
        due_open_sessions=lambda now: (
            AttendanceCandidate(20, 1, NOW, True),
            AttendanceCandidate(21, 1, NOW, False),
        ),
        revalidate=lambda session_id, recipient_id, event: session_id == 20,
    )
    dependencies = SimpleNamespace(
        clock=SimpleNamespace(now=lambda: NOW),
        tasks=tasks,
        attendance=attendance,
        unit_of_work_factory=lambda: SimpleNamespace(
            __enter__=lambda self: self,
            __exit__=lambda self, *args: None,
        ),
    )

    class UnitOfWork:
        def __enter__(self) -> UnitOfWork:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    dependencies.unit_of_work_factory = UnitOfWork
    occurrences = SimpleNamespace(record=lambda item: recorded.append(item) or True)

    assert OccurrenceDispatcher(dependencies, occurrences).dispatch() == 2
    assert [item.event_type for item in recorded] == [
        NotificationEventType.TASK_UPCOMING,
        NotificationEventType.ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END,
    ]
