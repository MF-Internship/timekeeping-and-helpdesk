from typing import Protocol


class AttendanceNotificationSink(Protocol):
    def suppress_open_session_reminder(self, session_id: int, owner_id: int) -> None: ...


class NoopAttendanceNotificationSink:
    def suppress_open_session_reminder(self, session_id: int, owner_id: int) -> None:
        return None
