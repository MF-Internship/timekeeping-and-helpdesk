from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from attendance.domain.attendance import (
    AttendanceKind,
    AttendanceResolutionMethod,
    LocationMatch,
    LocationSnapshot,
    LocationValidationResult,
)


@dataclass(frozen=True, slots=True)
class AttendanceCommand:
    latitude: Decimal
    longitude: Decimal
    accuracy_m: Decimal
    captured_at: datetime | None = None
    selected_location_id: int | None = None
    device_metadata: dict[str, object] | None = None
    request_ip: str | None = None


@dataclass(frozen=True, slots=True)
class AttendanceSnapshot:
    id: int
    user_id: int
    kind: AttendanceKind
    work_date: date
    recorded_at: datetime
    captured_at: datetime | None
    captured_latitude: Decimal
    captured_longitude: Decimal
    accuracy_m: Decimal
    location: LocationSnapshot
    distance_m: Decimal
    validation_result: LocationValidationResult
    resolution_method: AttendanceResolutionMethod


@dataclass(frozen=True, slots=True)
class AcceptedPunchRequest:
    user_id: int
    kind: AttendanceKind
    work_date: date
    recorded_at: datetime
    command: AttendanceCommand
    match: LocationMatch
    resolution: AttendanceResolutionMethod


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    max_attendance_accuracy_m: Decimal
    timezone: str
    shift_start: time
    shift_end: time
    late_grace_minutes: int
    early_checkout_grace_minutes: int
    late_checkout_grace_minutes: int


@dataclass(frozen=True, slots=True)
class ReferenceSnapshot:
    config: ConfigSnapshot
    locations: tuple[LocationSnapshot, ...]


@dataclass(frozen=True, slots=True)
class SessionProjection:
    id: int
    work_date: date
    check_in_at: datetime
    check_out_at: datetime | None
    check_in_location_id: int
    check_out_location_id: int | None
    duration_minutes: Decimal | None
    closed_by_job: bool


@dataclass(frozen=True, slots=True)
class IndexedPunch:
    attendance: AttendanceSnapshot
    punch_index: int


@dataclass(frozen=True, slots=True)
class CommandResult:
    attendance: AttendanceSnapshot
    session: SessionProjection
    punch_index: int


@dataclass(frozen=True, slots=True)
class TodayAttendance:
    work_date: date
    punches: tuple[IndexedPunch, ...]
    sessions: tuple[SessionProjection, ...]
    total_duration_minutes: Decimal
    has_open_session: bool
