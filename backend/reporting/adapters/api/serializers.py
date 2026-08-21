from __future__ import annotations

from rest_framework import serializers

from reporting.application.dto import AttendanceReport, FailureRate, TaskReport


class FailureRateSerializer(serializers.Serializer[FailureRate]):
    numerator = serializers.IntegerField()
    denominator = serializers.IntegerField()
    excluded_count = serializers.IntegerField()
    rate_percent = serializers.FloatField(allow_null=True)


class AttendanceReportSerializer(serializers.Serializer[AttendanceReport]):
    users_in_open_session = serializers.IntegerField()
    users_no_check_in_today = serializers.IntegerField()
    users_checked_out_today = serializers.IntegerField()
    punch_count = serializers.IntegerField()
    total_valid_worked_minutes = serializers.FloatField()
    system_closed_missing_checkout_sessions = serializers.IntegerField()
    anomaly_counts = serializers.DictField(child=serializers.IntegerField())
    attempt_counts = serializers.DictField(child=serializers.IntegerField())
    rejected_attempt_diagnostics = serializers.DictField(child=serializers.IntegerField())
    nearest_location_diagnostics = serializers.DictField(child=serializers.IntegerField())
    failure_rate = FailureRateSerializer()


class TaskReportSerializer(serializers.Serializer[TaskReport]):
    total_tasks = serializers.IntegerField()
    status_counts = serializers.DictField(child=serializers.IntegerField())
    completion_method_counts = serializers.DictField(child=serializers.IntegerField())
    gps_quality_counts = serializers.DictField(child=serializers.IntegerField())
    actual_completer_counts = serializers.DictField(child=serializers.IntegerField())
    assigned_task_closed_count = serializers.IntegerField()


def attendance_payload(report: AttendanceReport) -> dict[str, object]:
    return {
        "users_in_open_session": report.users_in_open_session,
        "users_no_check_in_today": report.users_no_check_in_today,
        "users_checked_out_today": report.users_checked_out_today,
        "punch_count": report.punch_count,
        "total_valid_worked_minutes": report.total_valid_worked_minutes,
        "system_closed_missing_checkout_sessions": report.system_closed_missing_checkout_sessions,
        "anomaly_counts": report.anomaly_counts,
        "attempt_counts": report.attempt_counts,
        "rejected_attempt_diagnostics": report.rejected_attempt_diagnostics,
        "nearest_location_diagnostics": report.nearest_location_diagnostics,
        "failure_rate": failure_rate_payload(report.failure_rate),
    }


def task_payload(report: TaskReport) -> dict[str, object]:
    return {
        "total_tasks": report.total_tasks,
        "status_counts": report.status_counts,
        "completion_method_counts": report.completion_method_counts,
        "gps_quality_counts": report.gps_quality_counts,
        "actual_completer_counts": report.actual_completer_counts,
        "assigned_task_closed_count": report.assigned_task_closed_count,
    }


def failure_rate_payload(rate: FailureRate) -> dict[str, object]:
    return {
        "numerator": rate.numerator,
        "denominator": rate.denominator,
        "excluded_count": rate.excluded_count,
        "rate_percent": rate.rate_percent,
    }

