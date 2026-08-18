from zoneinfo import ZoneInfo

from attendance.application.dependencies import AttendanceDependencies
from attendance.application.dto import TodayAttendance
from attendance.application.projections import indexed_punches


class AttendanceQueryService:
    def __init__(self, dependencies: AttendanceDependencies) -> None:
        self._dependencies = dependencies

    def today(self, actor_id: int) -> TodayAttendance:
        self._dependencies.authorization.authorize_view_self(actor_id)
        work_date = self._dependencies.clock.now().astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
        punches = self._dependencies.repository.punches(actor_id, work_date)
        sessions = self._dependencies.repository.sessions(actor_id, work_date)
        return TodayAttendance(
            work_date,
            indexed_punches(punches),
            sessions,
            self._dependencies.repository.total_duration(actor_id, work_date),
            any(session.check_out_at is None and not session.closed_by_job for session in sessions),
        )
