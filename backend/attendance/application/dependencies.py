from collections.abc import Callable
from dataclasses import dataclass, field

from attendance.ports.attempts import AttemptWriter
from attendance.ports.authorization import AttendanceAuthorization
from attendance.ports.clock import Clock
from attendance.ports.notifications import (
    AttendanceNotificationSink,
    NoopAttendanceNotificationSink,
)
from attendance.ports.reference_data import ReferenceData
from attendance.ports.repositories import AttendanceRepository
from attendance.ports.unit_of_work import UnitOfWork
from audit.ports.recording import AuditRecorder


@dataclass(frozen=True, slots=True)
class AttendanceDependencies:
    authorization: AttendanceAuthorization
    clock: Clock
    reference_data: ReferenceData
    repository: AttendanceRepository
    attempts: AttemptWriter
    audit: AuditRecorder
    unit_of_work_factory: Callable[[], UnitOfWork]
    notifications: AttendanceNotificationSink = field(
        default_factory=NoopAttendanceNotificationSink
    )
