from collections.abc import Callable

from django.urls import URLPattern, path

from attendance.adapters.api.views import CheckInView, CheckOutView, TodayAttendanceView
from attendance.application.container import AttendanceContainer


def attendance_urlpatterns(
    container_provider: Callable[[], AttendanceContainer],
) -> list[URLPattern]:
    CheckInView.container_provider = staticmethod(container_provider)
    CheckOutView.container_provider = staticmethod(container_provider)
    TodayAttendanceView.container_provider = staticmethod(container_provider)
    return [
        path("attendance/check-in", CheckInView.as_view(), name="attendance-check-in"),
        path("attendance/check-out", CheckOutView.as_view(), name="attendance-check-out"),
        path("attendance/today", TodayAttendanceView.as_view(), name="attendance-today"),
    ]
