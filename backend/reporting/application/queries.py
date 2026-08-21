from __future__ import annotations

from dataclasses import dataclass

from audit.ports.recording import AuditAction, AuditEntry, AuditRecorder
from reporting.application.dto import AttendanceReport, ReportFilters, TaskReport
from reporting.ports.authorization import ReportingAuthorization
from reporting.ports.repositories import ReportingRepository


@dataclass(frozen=True, slots=True)
class ReportingDependencies:
    authorization: ReportingAuthorization
    repository: ReportingRepository
    audit: AuditRecorder


class ReportingQueryService:
    def __init__(self, dependencies: ReportingDependencies) -> None:
        self._dependencies = dependencies

    def attendance(self, filters: ReportFilters) -> AttendanceReport:
        scope_all = self._authorize_view(filters)
        return self._dependencies.repository.attendance_report(filters, scope_all=scope_all)

    def tasks(self, filters: ReportFilters) -> TaskReport:
        scope_all = self._authorize_view(filters)
        return self._dependencies.repository.task_report(filters, scope_all=scope_all)

    def export_attendance(self, filters: ReportFilters) -> str:
        self._dependencies.authorization.authorize_export(filters.actor_id)
        report = self._dependencies.repository.attendance_report(filters, scope_all=True)
        self._audit_export(filters, "attendance", _row_count(report.attempt_counts))
        return _attendance_csv(report, filters.include_sensitive_coordinates)

    def export_tasks(self, filters: ReportFilters) -> str:
        self._dependencies.authorization.authorize_export(filters.actor_id)
        report = self._dependencies.repository.task_report(filters, scope_all=True)
        self._audit_export(filters, "tasks", report.total_tasks)
        return _task_csv(report)

    def _authorize_view(self, filters: ReportFilters) -> bool:
        return self._dependencies.authorization.authorize_view(filters.actor_id)

    def _audit_export(self, filters: ReportFilters, report_type: str, row_count: int) -> None:
        self._dependencies.audit.append_audit_entry(
            AuditEntry(
                actor_id=filters.actor_id,
                action=AuditAction.REPORT_EXPORTED,
                target_type="Report",
                target_id=report_type,
                before={},
                after={
                    "report_type": report_type,
                    "start_date": filters.start_date.isoformat(),
                    "end_date": filters.end_date.isoformat(),
                    "user_id": filters.user_id,
                    "include_sensitive_coordinates": filters.include_sensitive_coordinates,
                    "row_count": row_count,
                },
            )
        )


def _row_count(counts: dict[str, int]) -> int:
    return sum(counts.values())


def _attendance_csv(report: AttendanceReport, include_sensitive_coordinates: bool) -> str:
    coordinate_policy = "included" if include_sensitive_coordinates else "excluded"
    lines = [
        "metric,value",
        f"users_in_open_session,{report.users_in_open_session}",
        f"users_no_check_in_today,{report.users_no_check_in_today}",
        f"users_checked_out_today,{report.users_checked_out_today}",
        f"punch_count,{report.punch_count}",
        f"total_valid_worked_minutes,{report.total_valid_worked_minutes}",
        f"system_closed_missing_checkout_sessions,{report.system_closed_missing_checkout_sessions}",
        f"failure_numerator,{report.failure_rate.numerator}",
        f"failure_denominator,{report.failure_rate.denominator}",
        f"failure_excluded_count,{report.failure_rate.excluded_count}",
        f"failure_rate_percent,{report.failure_rate.rate_percent or 'N/A'}",
        f"sensitive_coordinates,{coordinate_policy}",
    ]
    return "\n".join(lines) + "\n"


def _task_csv(report: TaskReport) -> str:
    lines = ["metric,value", f"total_tasks,{report.total_tasks}"]
    lines.extend(f"status_{key},{value}" for key, value in sorted(report.status_counts.items()))
    lines.extend(
        f"completion_method_{key},{value}"
        for key, value in sorted(report.completion_method_counts.items())
    )
    lines.append(f"assigned_task_closed_count,{report.assigned_task_closed_count}")
    return "\n".join(lines) + "\n"
