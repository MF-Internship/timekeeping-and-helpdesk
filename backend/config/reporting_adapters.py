from __future__ import annotations

from collections import Counter
from datetime import date

from django.db.models import QuerySet, Sum
from django.utils import timezone

from attendance.domain.attempts import FAILURE_OUTCOMES, AttendanceAttemptOutcome
from attendance.models import Attendance, AttendanceAnomaly, AttendanceAttempt, AttendanceSession
from identity.application.authorization import DjangoAuthorizationGateway
from identity.domain.authorization import PermissionAction
from identity.models import User
from reporting.application.dto import AttendanceReport, FailureRate, ReportFilters, TaskReport
from tasks.domain.evidence import GpsQuality
from tasks.domain.tasks import CompletionMethod, TaskStatus
from tasks.models import Task, TaskAssignee, TaskUpdate


class DjangoReportingRepository:
    def attendance_report(self, filters: ReportFilters, *, scope_all: bool) -> AttendanceReport:
        user_ids = _visible_user_ids(filters, scope_all)
        attendances = Attendance.objects.filter(
            user_id__in=user_ids, work_date__range=(filters.start_date, filters.end_date)
        )
        sessions = AttendanceSession.objects.filter(
            user_id__in=user_ids, work_date__range=(filters.start_date, filters.end_date)
        )
        attempts = AttendanceAttempt.objects.filter(
            user_id__in=user_ids, work_date__range=(filters.start_date, filters.end_date)
        )
        return AttendanceReport(
            users_in_open_session=_open_sessions_today(user_ids),
            users_no_check_in_today=_no_check_in_today(user_ids),
            users_checked_out_today=_checked_out_today(user_ids),
            punch_count=attendances.count(),
            total_valid_worked_minutes=float(
                sessions.filter(closed_by_job=False).aggregate(value=Sum("duration_minutes"))[
                    "value"
                ]
                or 0
            ),
            system_closed_missing_checkout_sessions=sessions.filter(closed_by_job=True).count(),
            anomaly_counts=_counter(
                AttendanceAnomaly.objects.filter(attendance__in=attendances), "reason"
            ),
            attempt_counts=_counter(attempts, "outcome"),
            rejected_attempt_diagnostics=_rejected_diagnostics(attempts),
            nearest_location_diagnostics=_nearest_diagnostics(attempts),
            failure_rate=_failure_rate(attempts),
        )

    def task_report(self, filters: ReportFilters, *, scope_all: bool) -> TaskReport:
        user_ids = _visible_user_ids(filters, scope_all)
        tasks = Task.objects.filter(assigned_date__range=(filters.start_date, filters.end_date))
        if not scope_all:
            tasks = tasks.filter(assignee_links__user_id=filters.actor_id)
        elif filters.user_id is not None:
            tasks = tasks.filter(assignee_links__user_id=filters.user_id)
        tasks = tasks.filter(deleted_at__isnull=True).distinct()
        updates = TaskUpdate.objects.filter(task__in=tasks)
        return TaskReport(
            total_tasks=tasks.count(),
            status_counts=_all_counts(tasks, "status", [value.value for value in TaskStatus]),
            completion_method_counts=_all_counts(
                tasks.filter(status=TaskStatus.COMPLETED.value),
                "completion_method",
                [value.value for value in CompletionMethod],
            ),
            gps_quality_counts=_all_counts(
                updates.exclude(gps_quality__isnull=True),
                "gps_quality",
                [value.value for value in GpsQuality],
            ),
            actual_completer_counts=_actual_completers(tasks),
            assigned_task_closed_count=TaskAssignee.objects.filter(
                task__in=tasks,
                task__status=TaskStatus.COMPLETED.value,
                user_id__in=user_ids,
            ).count(),
        )


def _visible_user_ids(filters: ReportFilters, scope_all: bool) -> tuple[int, ...]:
    if not scope_all:
        return (filters.actor_id,)
    queryset = User.objects.all()
    if filters.user_id is not None:
        queryset = queryset.filter(pk=filters.user_id)
    return tuple(queryset.values_list("id", flat=True))


def _today() -> date:
    return timezone.localdate()


def _open_sessions_today(user_ids: tuple[int, ...]) -> int:
    return (
        AttendanceSession.objects.filter(
            user_id__in=user_ids, work_date=_today(), check_out__isnull=True, closed_by_job=False
        )
        .values("user_id")
        .distinct()
        .count()
    )


def _no_check_in_today(user_ids: tuple[int, ...]) -> int:
    checked_in = Attendance.objects.filter(
        user_id__in=user_ids, work_date=_today(), kind="IN"
    ).values("user_id")
    return User.objects.filter(id__in=user_ids, role="HELPDESK").exclude(id__in=checked_in).count()


def _checked_out_today(user_ids: tuple[int, ...]) -> int:
    return (
        AttendanceSession.objects.filter(
            user_id__in=user_ids, work_date=_today(), check_out__isnull=False
        )
        .values("user_id")
        .distinct()
        .count()
    )


def _counter(queryset: QuerySet, field: str) -> dict[str, int]:
    return dict(Counter(queryset.values_list(field, flat=True)))


def _all_counts(queryset: QuerySet, field: str, values: list[str]) -> dict[str, int]:
    counts = _counter(queryset, field)
    return {value: counts.get(value, 0) for value in values}


def _rejected_diagnostics(attempts: QuerySet[AttendanceAttempt]) -> dict[str, int]:
    return _counter(attempts.exclude(outcome=AttendanceAttemptOutcome.ACCEPTED.value), "outcome")


def _nearest_diagnostics(attempts: QuerySet[AttendanceAttempt]) -> dict[str, int]:
    coverage = Counter(
        "observed" if nearest_id else "missing"
        for nearest_id in attempts.values_list("nearest_location_id", flat=True)
    )
    return dict(coverage)


def _failure_rate(attempts: QuerySet[AttendanceAttempt]) -> FailureRate:
    excluded = attempts.filter(outcome=AttendanceAttemptOutcome.LOCATION_CHOICE_REQUIRED.value)
    denominator = attempts.exclude(
        outcome=AttendanceAttemptOutcome.LOCATION_CHOICE_REQUIRED.value
    ).count()
    numerator = attempts.filter(outcome__in=[value.value for value in FAILURE_OUTCOMES]).count()
    return FailureRate(numerator, denominator, excluded.count())


def _actual_completers(tasks: QuerySet[Task]) -> dict[str, int]:
    counts = Counter(
        str(value)
        for value in tasks.filter(completed_by_id__isnull=False).values_list(
            "completed_by_id", flat=True
        )
    )
    return dict(counts)


class DjangoReportingAuthorization:
    def __init__(self) -> None:
        self._gateway = DjangoAuthorizationGateway()

    def authorize_view(self, actor_id: int) -> bool:
        decision = self._gateway.authorize(actor_id, PermissionAction.REPORT_VIEW_SELF)
        return decision.granted_by is PermissionAction.REPORT_VIEW_ALL

    def authorize_export(self, actor_id: int) -> None:
        self._gateway.authorize(actor_id, PermissionAction.REPORT_EXPORT)
