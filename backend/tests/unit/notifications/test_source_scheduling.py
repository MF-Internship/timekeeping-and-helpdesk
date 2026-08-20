from __future__ import annotations

from datetime import date, datetime, time
from types import SimpleNamespace

import pytest

import attendance.adapters.notification_facts as attendance_facts
from attendance.adapters.notification_facts import DjangoAttendanceNotificationFacts
from tasks.adapters.notification_facts import LOCAL_TIMEZONE, DjangoTaskNotificationFacts


@pytest.mark.unit
def test_task_scans_start_at_exact_approved_local_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts = DjangoTaskNotificationFacts(SimpleNamespace())
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(facts, "_candidates", lambda **filters: calls.append(filters) or ())
    day = date(2026, 8, 21)

    assert facts.due_upcoming(datetime.combine(day, time(16, 59), LOCAL_TIMEZONE)) == ()
    assert calls == []
    assert facts.due_upcoming(datetime.combine(day, time(17), LOCAL_TIMEZONE)) == ()
    assert calls.pop() == {"assigned_date": date(2026, 8, 22)}

    assert facts.due_overdue(datetime.combine(day, time(7, 59), LOCAL_TIMEZONE)) == ()
    assert calls == []
    assert facts.due_overdue(datetime.combine(day, time(8), LOCAL_TIMEZONE)) == ()
    assert calls.pop() == {"assigned_date__lt": day}


@pytest.mark.unit
def test_attendance_scan_starts_at_shift_end_minus_thirty_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = SimpleNamespace(pk=7, user_id=3, work_date=date(2026, 8, 21))

    class Rows:
        def filter(self, **filters: object) -> Rows:
            return self

        def order_by(self, field: str) -> tuple[SimpleNamespace, ...]:
            return (row,)

    monkeypatch.setattr(
        attendance_facts,
        "AttendanceSession",
        SimpleNamespace(objects=Rows()),
    )
    facts = DjangoAttendanceNotificationFacts(SimpleNamespace(), lambda: time(17))

    before = datetime(2026, 8, 21, 16, 29, tzinfo=LOCAL_TIMEZONE)
    boundary = datetime(2026, 8, 21, 16, 30, tzinfo=LOCAL_TIMEZONE)
    assert facts.due_open_sessions(before) == ()
    candidates = facts.due_open_sessions(boundary)
    assert len(candidates) == 1
    assert candidates[0].reminder_at == boundary
