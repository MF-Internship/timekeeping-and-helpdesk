from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class ReportFilters:
    actor_id: int
    start_date: date
    end_date: date
    user_id: int | None = None
    include_sensitive_coordinates: bool = False


@dataclass(frozen=True, slots=True)
class FailureRate:
    numerator: int
    denominator: int
    excluded_count: int

    @property
    def rate_percent(self) -> float | None:
        if self.denominator == 0:
            return None
        return round((self.numerator / self.denominator) * 100, 2)


@dataclass(frozen=True, slots=True)
class AttendanceReport:
    users_in_open_session: int
    users_no_check_in_today: int
    users_checked_out_today: int
    punch_count: int
    total_valid_worked_minutes: float
    system_closed_missing_checkout_sessions: int
    anomaly_counts: dict[str, int]
    attempt_counts: dict[str, int]
    rejected_attempt_diagnostics: dict[str, int]
    nearest_location_diagnostics: dict[str, int]
    failure_rate: FailureRate


@dataclass(frozen=True, slots=True)
class TaskReport:
    total_tasks: int
    status_counts: dict[str, int]
    completion_method_counts: dict[str, int]
    gps_quality_counts: dict[str, int]
    actual_completer_counts: dict[str, int]
    assigned_task_closed_count: int
