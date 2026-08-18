from datetime import UTC, datetime, time
from decimal import Decimal

from attendance.application.anomalies import reconcile_punch_anomalies
from attendance.application.dto import AttendanceSnapshot, ConfigSnapshot
from attendance.domain.attendance import (
    AttendanceAnomalyReason,
    AttendanceKind,
    AttendanceResolutionMethod,
    LocationSnapshot,
    LocationValidationResult,
)

LOCATION = LocationSnapshot(1, "A", "A", "A", Decimal("10"), Decimal("106"), Decimal("50"), True)
CONFIG = ConfigSnapshot(Decimal("25"), "Asia/Ho_Chi_Minh", time(8), time(17), 15, 10, 60)


class Repository:
    def __init__(self) -> None:
        self.values: dict[int, tuple[AttendanceAnomalyReason, ...]] = {}

    def replace_anomalies(
        self, attendance_id: int, reasons: tuple[AttendanceAnomalyReason, ...]
    ) -> None:
        self.values[attendance_id] = reasons


def punch(identifier: int, kind: AttendanceKind, hour: int, minute: int = 0) -> AttendanceSnapshot:
    recorded = datetime(2026, 8, 18, hour, minute, tzinfo=UTC)
    return AttendanceSnapshot(
        identifier,
        1,
        kind,
        recorded.date(),
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


def test_only_first_in_and_latest_out_keep_governed_anomalies() -> None:
    repository = Repository()
    punches = (
        punch(1, AttendanceKind.IN, 1, 16),
        punch(2, AttendanceKind.OUT, 8, 49),
        punch(3, AttendanceKind.IN, 9),
        punch(4, AttendanceKind.OUT, 11, 1),
    )
    for index, current in enumerate(punches, start=1):
        reconcile_punch_anomalies(repository, punches[:index], current, CONFIG)  # type: ignore[arg-type]
    assert repository.values[1] == (AttendanceAnomalyReason.LATE_CHECK_IN,)
    assert repository.values[3] == ()
    assert repository.values[2] == ()
    assert repository.values[4] == (AttendanceAnomalyReason.LATE_CHECK_OUT,)


def test_checkout_equality_boundaries_are_not_anomalies() -> None:
    repository = Repository()
    early_equal = punch(1, AttendanceKind.OUT, 9, 50)
    late_equal = punch(2, AttendanceKind.OUT, 11)
    reconcile_punch_anomalies(repository, (early_equal,), early_equal, CONFIG)  # type: ignore[arg-type]
    reconcile_punch_anomalies(repository, (early_equal, late_equal), late_equal, CONFIG)  # type: ignore[arg-type]
    assert repository.values == {1: (), 2: ()}
