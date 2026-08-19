from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import pytest

from attendance.application.dependencies import AttendanceDependencies
from attendance.application.dto import AttendanceSnapshot, SessionProjection
from attendance.application.queries import AttendanceQueryService
from attendance.domain.attendance import (
    AttendanceKind,
    AttendanceResolutionMethod,
    LocationSnapshot,
    LocationValidationResult,
)

LOCATION = LocationSnapshot(1, "A", "A", "A", Decimal("10"), Decimal("106"), Decimal("50"), True)


def punch(identifier: int, minute: int) -> AttendanceSnapshot:
    recorded = datetime(2026, 8, 17, 17, minute, tzinfo=UTC)
    return AttendanceSnapshot(
        identifier,
        42,
        AttendanceKind.IN if identifier % 2 else AttendanceKind.OUT,
        date(2026, 8, 18),
        recorded,
        None,
        Decimal("10"),
        Decimal("106"),
        Decimal("5"),
        LOCATION,
        Decimal("0"),
        LocationValidationResult.INSIDE_GEOFENCE,
        AttendanceResolutionMethod.AUTO_SINGLE,
    )


class Authorization:
    actor_id: int | None = None

    def authorize_view_self(self, actor_id: int) -> None:
        self.actor_id = actor_id


class Clock:
    def now(self) -> datetime:
        return datetime(2026, 8, 17, 17, 30, tzinfo=UTC)


class Repository:
    def __init__(self, completed_count: int = 1) -> None:
        self.calls: list[tuple[int, date]] = []
        self.completed_count = completed_count

    def punches(self, user_id: int, work_date: date) -> tuple[AttendanceSnapshot, ...]:
        self.calls.append((user_id, work_date))
        return (punch(2, 20), punch(1, 10))

    def sessions(self, user_id: int, work_date: date) -> tuple[SessionProjection, ...]:
        completed = tuple(
            SessionProjection(
                identifier,
                work_date,
                punch(1, 10).recorded_at,
                punch(2, 20).recorded_at,
                1,
                1,
                Decimal("10"),
                False,
            )
            for identifier in range(1, self.completed_count + 1)
        )
        return (
            *completed,
            SessionProjection(2, work_date, punch(2, 20).recorded_at, None, 1, None, None, False),
            SessionProjection(3, work_date, punch(2, 20).recorded_at, None, 1, None, None, True),
        )

    def total_duration(self, user_id: int, work_date: date) -> Decimal:
        return Decimal(self.completed_count * 10).quantize(Decimal("0.000001"))


def test_today_uses_local_date_actor_scope_order_index_duration_and_open_predicate() -> None:
    authorization, repository = Authorization(), Repository()
    dependencies = AttendanceDependencies(
        authorization,
        Clock(),
        cast(Any, None),
        cast(Any, repository),
        cast(Any, None),
        cast(Any, None),
        cast(Any, None),
    )
    result = AttendanceQueryService(dependencies).today(42)
    assert authorization.actor_id == 42
    assert repository.calls == [(42, date(2026, 8, 18))]
    assert [(item.attendance.id, item.punch_index) for item in result.punches] == [(1, 1), (2, 2)]
    assert result.total_duration_minutes == Decimal("10.000000")
    assert result.has_open_session is True


@pytest.mark.unit
@pytest.mark.parametrize("completed_count", range(1, 21))
def test_today_preserves_one_to_twenty_sessions_and_excludes_incomplete(
    completed_count: int,
) -> None:
    repository = Repository(completed_count)
    dependencies = AttendanceDependencies(
        Authorization(),
        Clock(),
        cast(Any, None),
        cast(Any, repository),
        cast(Any, None),
        cast(Any, None),
        cast(Any, None),
    )
    result = AttendanceQueryService(dependencies).today(42)
    assert len(result.sessions) == completed_count + 2
    assert result.total_duration_minutes == Decimal(completed_count * 10).quantize(
        Decimal("0.000001")
    )
