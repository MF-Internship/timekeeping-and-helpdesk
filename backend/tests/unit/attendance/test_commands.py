from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from types import TracebackType

import pytest

from attendance.application.commands import AttendanceCommandService
from attendance.application.dependencies import AttendanceDependencies
from attendance.application.dto import (
    AcceptedPunchRequest,
    AttendanceCommand,
    AttendanceSnapshot,
    ConfigSnapshot,
    ReferenceSnapshot,
    SessionProjection,
)
from attendance.domain.attendance import (
    AttendanceKind,
    LocationSnapshot,
    LocationValidationResult,
)
from attendance.domain.sessions import SessionSnapshot, duration_minutes
from attendance.ports.attempts import AttemptDraft
from audit.domain.records import AuditEntry, OutboxRecord
from core.errors import IdentityAPIError

NOW = datetime(2026, 8, 18, 1, tzinfo=UTC)
LOCATION = LocationSnapshot(
    7,
    "HCM000007",
    "Location 7",
    "Address 7",
    Decimal("10"),
    Decimal("106"),
    Decimal("50"),
    True,
)
COMMAND = AttendanceCommand(Decimal("10"), Decimal("106"), Decimal("5"))


class Authorization:
    def authorize_check_in(self, actor_id: int) -> None:
        assert actor_id == 42

    def authorize_check_out(self, actor_id: int) -> None:
        assert actor_id == 42

    def authorize_view_self(self, actor_id: int) -> None:
        assert actor_id == 42


class Clock:
    value = NOW

    def now(self) -> datetime:
        value = self.value
        self.value += __import__("datetime").timedelta(minutes=30)
        return value


class ReferenceData:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def load_locked(self) -> ReferenceSnapshot:
        if self.fail:
            raise RuntimeError("infrastructure secret")
        config = ConfigSnapshot(Decimal("25"), "Asia/Ho_Chi_Minh", time(8), time(17), 15, 10, 60)
        return ReferenceSnapshot(config, (LOCATION,))

    def distance_m(
        self, latitude: Decimal, longitude: Decimal, location: LocationSnapshot
    ) -> Decimal:
        return Decimal("40")


class UnitOfWork:
    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class Attempts:
    def __init__(self, *, fail: bool = False) -> None:
        self.values: list[AttemptDraft] = []
        self.fail = fail

    def append(self, draft: AttemptDraft) -> None:
        self.values.append(draft)
        if self.fail:
            raise RuntimeError("writer secret")


class Audit:
    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []
        self.outbox: list[OutboxRecord] = []

    def append_audit_entry(self, entry: AuditEntry) -> None:
        self.entries.append(entry)

    def append_outbox_event(self, event: OutboxRecord) -> None:
        self.outbox.append(event)


class Repository:
    def __init__(self) -> None:
        self.attendances: list[AttendanceSnapshot] = []
        self.open: SessionSnapshot | None = None
        self.anomalies: dict[int, tuple[object, ...]] = {}

    def open_session(self, user_id: int, *, lock: bool = False) -> SessionSnapshot | None:
        return self.open

    def create_attendance(self, request: AcceptedPunchRequest) -> AttendanceSnapshot:
        value = AttendanceSnapshot(
            len(self.attendances) + 1,
            request.user_id,
            request.kind,
            request.work_date,
            request.recorded_at,
            request.command.captured_at,
            request.command.latitude,
            request.command.longitude,
            request.command.accuracy_m,
            request.match.location,
            request.match.distance_m,
            LocationValidationResult.INSIDE_GEOFENCE,
            request.resolution,
        )
        self.attendances.append(value)
        return value

    def open_new_session(self, attendance: AttendanceSnapshot) -> SessionProjection:
        self.open = SessionSnapshot(
            10, attendance.user_id, attendance.work_date, attendance.id, None, None, False
        )
        return self._projection()

    def close_session(
        self, session: SessionSnapshot, attendance: AttendanceSnapshot
    ) -> SessionProjection:
        minutes = duration_minutes(self.attendances[0].recorded_at, attendance.recorded_at)
        projection = SessionProjection(
            session.id,
            session.work_date,
            self.attendances[0].recorded_at,
            attendance.recorded_at,
            LOCATION.id,
            LOCATION.id,
            minutes,
            False,
        )
        self.open = None
        return projection

    def punches(self, user_id: int, work_date: date) -> tuple[AttendanceSnapshot, ...]:
        return tuple(self.attendances)

    def sessions(self, user_id: int, work_date: date) -> tuple[SessionProjection, ...]:
        return ()

    def replace_anomalies(self, attendance_id: int, reasons: tuple[object, ...]) -> None:
        self.anomalies[attendance_id] = reasons

    def total_duration(self, user_id: int, work_date: date) -> Decimal:
        return Decimal("0")

    def _projection(self) -> SessionProjection:
        assert self.open is not None
        return SessionProjection(
            10,
            self.open.work_date,
            self.attendances[0].recorded_at,
            None,
            LOCATION.id,
            None,
            None,
            False,
        )


def service(
    *, writer_fails: bool = False, reference_fails: bool = False
) -> tuple[AttendanceCommandService, Repository, Attempts, Audit]:
    repository = Repository()
    attempts = Attempts(fail=writer_fails)
    audit = Audit()
    dependencies = AttendanceDependencies(
        Authorization(),
        Clock(),
        ReferenceData(fail=reference_fails),
        repository,
        attempts,
        audit,
        UnitOfWork,
    )
    return AttendanceCommandService(dependencies), repository, attempts, audit


def test_check_in_out_owns_fields_state_attempts_audit_and_projection() -> None:
    commands, repository, attempts, audit = service()
    check_in = commands.check_in(42, COMMAND)
    assert (check_in.attendance.user_id, check_in.attendance.kind, check_in.punch_index) == (
        42,
        AttendanceKind.IN,
        1,
    )
    with pytest.raises(IdentityAPIError) as duplicate:
        commands.check_in(42, COMMAND)
    assert duplicate.value.error_code == "SESSION_ALREADY_OPEN"
    check_out = commands.check_out(42, COMMAND)
    assert check_out.punch_index == 2
    assert check_out.session.duration_minutes == Decimal("60.000000")
    with pytest.raises(IdentityAPIError) as missing:
        commands.check_out(42, COMMAND)
    assert missing.value.error_code == "NO_OPEN_SESSION"
    assert [item.outcome.value for item in attempts.values] == [
        "ACCEPTED",
        "SESSION_ALREADY_OPEN",
        "ACCEPTED",
        "NO_OPEN_SESSION",
    ]
    assert [entry.action.value for entry in audit.entries] == [
        "attendance.check_in.created",
        "attendance.check_out.created",
    ]
    assert audit.outbox == [] and len(repository.attendances) == 2
    assert repository.anomalies[1] == ()


def test_attempt_writer_failure_does_not_change_accepted_result_or_retry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    commands, repository, attempts, _audit = service(writer_fails=True)
    result = commands.check_in(42, COMMAND)
    assert result.attendance.id == 1 and len(attempts.values) == 1
    assert len(repository.attendances) == 1
    assert "writer secret" not in caplog.text


def test_unexpected_infrastructure_failure_writes_no_attempt(
    caplog: pytest.LogCaptureFixture,
) -> None:
    commands, _repository, attempts, _audit = service(reference_fails=True)
    with pytest.raises(RuntimeError):
        commands.check_in(42, COMMAND)
    assert attempts.values == []
    assert "infrastructure secret" not in caplog.text
