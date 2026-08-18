from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from attendance.application.dto import AttendanceSnapshot, ConfigSnapshot
from attendance.domain.attendance import AttendanceAnomalyReason, AttendanceKind
from attendance.ports.repositories import AttendanceRepository


def reconcile_punch_anomalies(
    repository: AttendanceRepository,
    punches: tuple[AttendanceSnapshot, ...],
    current: AttendanceSnapshot,
    config: ConfigSnapshot,
) -> None:
    if current.kind is AttendanceKind.IN:
        _reconcile_in(repository, punches, current, config)
    else:
        _reconcile_out(repository, punches, current, config)


def _reconcile_in(
    repository: AttendanceRepository,
    punches: tuple[AttendanceSnapshot, ...],
    current: AttendanceSnapshot,
    config: ConfigSnapshot,
) -> None:
    first_in = next(item for item in punches if item.kind is AttendanceKind.IN)
    reasons: tuple[AttendanceAnomalyReason, ...] = ()
    if first_in.id == current.id and _local(current.recorded_at, config) > _shift(
        current.recorded_at, config, config.late_grace_minutes
    ):
        reasons = (AttendanceAnomalyReason.LATE_CHECK_IN,)
    repository.replace_anomalies(current.id, reasons)


def _reconcile_out(
    repository: AttendanceRepository,
    punches: tuple[AttendanceSnapshot, ...],
    current: AttendanceSnapshot,
    config: ConfigSnapshot,
) -> None:
    outs = tuple(item for item in punches if item.kind is AttendanceKind.OUT)
    for previous in outs[:-1]:
        repository.replace_anomalies(previous.id, ())
    local = _local(current.recorded_at, config)
    early = _shift(current.recorded_at, config, -config.early_checkout_grace_minutes, end=True)
    late = _shift(current.recorded_at, config, config.late_checkout_grace_minutes, end=True)
    reasons: tuple[AttendanceAnomalyReason, ...] = ()
    if local < early:
        reasons = (AttendanceAnomalyReason.EARLY_CHECK_OUT,)
    elif local > late:
        reasons = (AttendanceAnomalyReason.LATE_CHECK_OUT,)
    repository.replace_anomalies(current.id, reasons)


def _local(value: datetime, config: ConfigSnapshot) -> datetime:
    return value.astimezone(ZoneInfo(config.timezone))


def _shift(value: datetime, config: ConfigSnapshot, minutes: int, *, end: bool = False) -> datetime:
    local = _local(value, config)
    shift_time = config.shift_end if end else config.shift_start
    return local.replace(
        hour=shift_time.hour,
        minute=shift_time.minute,
        second=shift_time.second,
        microsecond=shift_time.microsecond,
    ) + timedelta(minutes=minutes)
