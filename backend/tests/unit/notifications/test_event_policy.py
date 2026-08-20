from datetime import UTC, date, datetime

import pytest

from notifications.domain.events import (
    SAFE_TITLES,
    NotificationEventType,
    NotificationTargetType,
    Occurrence,
)


def test_event_vocabulary_is_exactly_the_five_approved_events() -> None:
    assert {item.value for item in NotificationEventType} == {
        "TASK_ASSIGNED",
        "TASK_UPCOMING",
        "TASK_OVERDUE",
        "ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END",
        "MULTI_ASSIGNEE_TASK_COMPLETED",
    }
    assert set(SAFE_TITLES) == set(NotificationEventType)
    assert {item.value for item in NotificationTargetType} == {"TASK", "ATTENDANCE_SESSION"}
    with pytest.raises(ValueError):
        NotificationEventType("LOCK_RESET_PASSWORD")


def test_assignment_occurrence_key_uses_assignment_version() -> None:
    now = datetime(2026, 8, 21, tzinfo=UTC)
    first = Occurrence(
        NotificationEventType.TASK_ASSIGNED,
        NotificationTargetType.TASK,
        8,
        3,
        now,
        assignment_version=1,
    )
    reassigned = Occurrence(
        NotificationEventType.TASK_ASSIGNED,
        NotificationTargetType.TASK,
        8,
        3,
        now,
        assignment_version=2,
    )
    assert first.dedupe_key == "v1:TASK_ASSIGNED:8:3:1"
    assert first.dedupe_key != reassigned.dedupe_key
    assert len(first.collapse_key) <= 32


def test_scheduled_keys_include_the_approved_dates() -> None:
    now = datetime(2026, 8, 21, tzinfo=UTC)
    upcoming = Occurrence(
        NotificationEventType.TASK_UPCOMING,
        NotificationTargetType.TASK,
        4,
        7,
        now,
        assigned_date=date(2026, 8, 22),
    )
    overdue = Occurrence(
        NotificationEventType.TASK_OVERDUE,
        NotificationTargetType.TASK,
        4,
        7,
        now,
        occurrence_date=date(2026, 8, 21),
    )
    assert upcoming.dedupe_key.endswith(":2026-08-22")
    assert overdue.dedupe_key.endswith(":2026-08-21")
