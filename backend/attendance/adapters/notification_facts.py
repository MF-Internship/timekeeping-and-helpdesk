from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from attendance.models import AttendanceSession
from attendance.ports.authorization import AttendanceAuthorization
from attendance.ports.notification_facts import (
    AttendanceNotificationCandidate,
    AttendanceNotificationTarget,
)

LOCAL_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


class DjangoAttendanceNotificationFacts:
    def __init__(
        self,
        authorization: AttendanceAuthorization,
        shift_end: Callable[[], time],
    ) -> None:
        self._authorization = authorization
        self._shift_end = shift_end

    def due_open_sessions(self, now: datetime) -> tuple[AttendanceNotificationCandidate, ...]:
        local_now = now.astimezone(LOCAL_TIMEZONE)
        rows = AttendanceSession.objects.filter(
            check_out__isnull=True,
            closed_by_job=False,
            user__is_active=True,
            user__role="HELPDESK",
        ).order_by("id")
        candidates = tuple(self._candidate(row) for row in rows)
        return tuple(item for item in candidates if item.reminder_at <= local_now)

    def revalidate(self, session_id: int, recipient_id: int, event_type: str) -> bool:
        if event_type != "ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END":
            return False
        return (
            AttendanceSession.objects.select_for_update()
            .filter(
                pk=session_id,
                user_id=recipient_id,
                check_out__isnull=True,
                closed_by_job=False,
                user__is_active=True,
                user__role="HELPDESK",
            )
            .exists()
        )

    def resolve(self, actor_id: int, session_id: int) -> AttendanceNotificationTarget | None:
        self._authorization.authorize_view_self(actor_id)
        exists = AttendanceSession.objects.filter(pk=session_id, user_id=actor_id).exists()
        return AttendanceNotificationTarget("attendance", session_id) if exists else None

    def _candidate(self, session: AttendanceSession) -> AttendanceNotificationCandidate:
        reminder_at = datetime.combine(
            session.work_date,
            self._shift_end(),
            tzinfo=LOCAL_TIMEZONE,
        ) - timedelta(minutes=30)
        return AttendanceNotificationCandidate(
            session.pk,
            session.user_id,  # type: ignore[attr-defined]
            reminder_at,
            True,
        )
