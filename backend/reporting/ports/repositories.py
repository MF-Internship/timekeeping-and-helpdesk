from __future__ import annotations

from typing import Protocol

from reporting.application.dto import AttendanceReport, ReportFilters, TaskReport


class ReportingRepository(Protocol):
    def attendance_report(self, filters: ReportFilters, *, scope_all: bool) -> AttendanceReport: ...

    def task_report(self, filters: ReportFilters, *, scope_all: bool) -> TaskReport: ...

