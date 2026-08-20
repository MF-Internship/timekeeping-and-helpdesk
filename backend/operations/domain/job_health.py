from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from zoneinfo import ZoneInfo

from operations.domain.job_runs import JobRunSnapshot, JobRunStatus
from operations.ports.attendance_health import AttendanceHealthEvidence

TIMEZONE = "Asia/Ho_Chi_Minh"
CUTOFF = time(1)


class JobHealthState(StrEnum):
    OK = "ok"
    ALERT = "alert"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class JobHealthReasons:
    no_run_history: bool
    missing_timely_success: bool
    unfinished_run: bool
    stale_running: bool
    latest_terminal_failed: bool
    run_count_mismatch: bool
    persisted_evidence_mismatch: bool
    overdue_open_sessions: bool


@dataclass(frozen=True, slots=True)
class JobHealthSnapshot:
    state: JobHealthState
    timezone: str
    cutoff_at: datetime
    refreshed_at: datetime
    latest_run: JobRunSnapshot | None
    latest_successful_run: JobRunSnapshot | None
    overdue_open_session_count: int
    evidence: AttendanceHealthEvidence
    invariant_valid: bool
    reasons: JobHealthReasons


@dataclass(frozen=True, slots=True)
class JobHealthInputs:
    refreshed_at: datetime
    latest_run: JobRunSnapshot | None
    latest_successful: JobRunSnapshot | None
    latest_terminal: JobRunSnapshot | None
    unfinished: tuple[JobRunSnapshot, ...]
    evidence: AttendanceHealthEvidence


@dataclass(frozen=True, slots=True)
class _HealthFacts:
    cutoff: datetime
    timely: bool
    after_cutoff: bool
    count_mismatch: bool
    persisted_mismatch: bool
    stale: bool
    terminal_failed: bool


def evaluate_job_health(inputs: JobHealthInputs) -> JobHealthSnapshot:
    facts = _facts(inputs)
    evidence = inputs.evidence
    reasons = _reasons(inputs, facts)
    state = _state(inputs, facts)
    return JobHealthSnapshot(
        state,
        TIMEZONE,
        facts.cutoff,
        inputs.refreshed_at,
        inputs.latest_run,
        inputs.latest_successful,
        evidence.overdue_open_session_count,
        evidence,
        not facts.count_mismatch and not facts.persisted_mismatch,
        reasons,
    )


def _facts(inputs: JobHealthInputs) -> _HealthFacts:
    zone = ZoneInfo(TIMEZONE)
    local = inputs.refreshed_at.astimezone(zone)
    start_of_day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = local.replace(hour=CUTOFF.hour, minute=0, second=0, microsecond=0)
    timely = _timely(inputs, zone, start_of_day, cutoff)
    count_mismatch = _count_mismatch(inputs.latest_run)
    persisted_mismatch = bool(
        inputs.evidence.job_closed_without_anomaly_count
        or inputs.evidence.anomaly_without_job_closed_count
        or inputs.evidence.job_closed_session_count
        != inputs.evidence.missing_checkout_anomaly_count
    )
    stale = any(run.started_at.astimezone(zone) < start_of_day for run in inputs.unfinished)
    terminal_failed = bool(
        inputs.latest_terminal
        and inputs.latest_terminal.status in {JobRunStatus.PARTIAL_FAILED, JobRunStatus.FAILED}
    )
    return _HealthFacts(
        cutoff, timely, local >= cutoff, count_mismatch, persisted_mismatch, stale, terminal_failed
    )


def _timely(
    inputs: JobHealthInputs, zone: ZoneInfo, start_of_day: datetime, cutoff: datetime
) -> bool:
    return bool(
        inputs.latest_successful
        and inputs.latest_successful.finished_at
        and start_of_day <= inputs.latest_successful.finished_at.astimezone(zone) < cutoff
    )


def _count_mismatch(run: JobRunSnapshot | None) -> bool:
    return bool(
        run and (run.changed_count != run.anomaly_count or run.changed_count > run.scanned_count)
    )


def _reasons(inputs: JobHealthInputs, facts: _HealthFacts) -> JobHealthReasons:
    return JobHealthReasons(
        inputs.latest_run is None,
        facts.after_cutoff and not facts.timely,
        facts.after_cutoff and bool(inputs.unfinished),
        facts.stale,
        facts.terminal_failed,
        facts.count_mismatch,
        facts.persisted_mismatch,
        inputs.evidence.overdue_open_session_count > 0,
    )


def _state(inputs: JobHealthInputs, facts: _HealthFacts) -> JobHealthState:
    immediate = any(
        (facts.stale, facts.terminal_failed, facts.count_mismatch, facts.persisted_mismatch)
    )
    cutoff_alert = facts.after_cutoff and (
        not facts.timely
        or bool(inputs.unfinished)
        or inputs.evidence.overdue_open_session_count > 0
    )
    if immediate or cutoff_alert:
        return JobHealthState.ALERT
    return JobHealthState.UNKNOWN if inputs.latest_run is None else JobHealthState.OK
