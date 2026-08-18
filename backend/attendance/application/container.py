from dataclasses import dataclass

from attendance.application.commands import AttendanceCommandService
from attendance.application.queries import AttendanceQueryService
from attendance.ports.authorization import AttendanceAuthorization


@dataclass(frozen=True, slots=True)
class AttendanceContainer:
    authorization: AttendanceAuthorization
    commands: AttendanceCommandService
    queries: AttendanceQueryService
