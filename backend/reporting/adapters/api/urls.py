from __future__ import annotations

from collections.abc import Callable

from django.urls import path

from reporting.adapters.api.views import (
    AttendanceExportView,
    AttendanceReportView,
    TaskExportView,
    TaskReportView,
)
from reporting.application.container import ReportingContainer


def reporting_urlpatterns(
    container: Callable[[], ReportingContainer],
) -> list:
    for view in (AttendanceReportView, TaskReportView, AttendanceExportView, TaskExportView):
        view.container_provider = staticmethod(container)
    return [
        path("reports/attendance/", AttendanceReportView.as_view(), name="attendance-report"),
        path("reports/tasks/", TaskReportView.as_view(), name="task-report"),
        path(
            "reports/attendance/export/",
            AttendanceExportView.as_view(),
            name="attendance-report-export",
        ),
        path("reports/tasks/export/", TaskExportView.as_view(), name="task-report-export"),
    ]

