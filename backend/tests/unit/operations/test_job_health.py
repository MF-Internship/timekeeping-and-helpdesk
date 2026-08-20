from datetime import UTC, datetime

from operations.domain.job_health import JobHealthInputs, JobHealthState, evaluate_job_health
from operations.domain.job_runs import JobName, JobRunErrorCode, JobRunSnapshot, JobRunStatus
from operations.ports.attendance_health import AttendanceHealthEvidence

NOW = datetime(2026, 8, 19, 1, tzinfo=UTC)
EMPTY = AttendanceHealthEvidence(0, 0, 0, 0, 0)


def run(started: datetime, finished: datetime | None, status: JobRunStatus) -> JobRunSnapshot:
    error = (
        JobRunErrorCode.SESSION_PROCESSING_FAILED
        if status in {JobRunStatus.PARTIAL_FAILED, JobRunStatus.FAILED}
        else None
    )
    return JobRunSnapshot(1, JobName.MISSING_CHECK_OUT, started, finished, status, 0, 0, 0, error)


def test_never_run_is_unknown_before_cutoff_and_alert_at_cutoff() -> None:
    before = datetime(2026, 8, 18, 17, 30, tzinfo=UTC)
    assert (
        evaluate_job_health(JobHealthInputs(before, None, None, None, (), EMPTY)).state
        is JobHealthState.UNKNOWN
    )
    assert (
        evaluate_job_health(JobHealthInputs(NOW, None, None, None, (), EMPTY)).state
        is JobHealthState.ALERT
    )


def test_success_at_exclusive_cutoff_is_late() -> None:
    cutoff = datetime(2026, 8, 18, 18, tzinfo=UTC)
    successful = run(cutoff.replace(minute=0), cutoff, JobRunStatus.SUCCEEDED)
    health = evaluate_job_health(
        JobHealthInputs(cutoff, successful, successful, successful, (), EMPTY)
    )
    assert health.state is JobHealthState.ALERT
    assert health.reasons.missing_timely_success


def test_persisted_mismatch_alerts_before_cutoff() -> None:
    before = datetime(2026, 8, 18, 17, 30, tzinfo=UTC)
    evidence = AttendanceHealthEvidence(0, 1, 0, 1, 0)
    health = evaluate_job_health(JobHealthInputs(before, None, None, None, (), evidence))
    assert health.state is JobHealthState.ALERT
    assert not health.invariant_valid


def test_current_running_is_allowed_before_cutoff_but_prior_day_running_is_stale() -> None:
    before = datetime(2026, 8, 18, 17, 30, tzinfo=UTC)
    current = run(datetime(2026, 8, 18, 17, 5, tzinfo=UTC), None, JobRunStatus.RUNNING)
    allowed = evaluate_job_health(JobHealthInputs(before, current, None, None, (current,), EMPTY))
    assert allowed.state is JobHealthState.OK
    prior = run(datetime(2026, 8, 17, 17, 5, tzinfo=UTC), None, JobRunStatus.RUNNING)
    stale = evaluate_job_health(JobHealthInputs(before, prior, None, None, (prior,), EMPTY))
    assert stale.state is JobHealthState.ALERT
    assert stale.reasons.stale_running


def test_timely_success_is_ok_but_late_success_and_unfinished_after_cutoff_alert() -> None:
    refreshed = datetime(2026, 8, 18, 18, 5, tzinfo=UTC)
    timely = run(
        datetime(2026, 8, 18, 17, 30, tzinfo=UTC),
        datetime(2026, 8, 18, 17, 59, tzinfo=UTC),
        JobRunStatus.SUCCEEDED,
    )
    assert (
        evaluate_job_health(JobHealthInputs(refreshed, timely, timely, timely, (), EMPTY)).state
        is JobHealthState.OK
    )
    running = run(datetime(2026, 8, 18, 18, tzinfo=UTC), None, JobRunStatus.RUNNING)
    health = evaluate_job_health(
        JobHealthInputs(refreshed, running, timely, timely, (running,), EMPTY)
    )
    assert health.state is JobHealthState.ALERT
    assert health.reasons.unfinished_run


def test_terminal_failure_alerts_and_overdue_only_alerts_after_cutoff() -> None:
    before = datetime(2026, 8, 18, 17, 30, tzinfo=UTC)
    failed = run(before, before, JobRunStatus.FAILED)
    assert (
        evaluate_job_health(JobHealthInputs(before, failed, None, failed, (), EMPTY)).state
        is JobHealthState.ALERT
    )
    overdue = AttendanceHealthEvidence(1, 0, 0, 0, 0)
    assert (
        evaluate_job_health(JobHealthInputs(before, None, None, None, (), overdue)).state
        is JobHealthState.UNKNOWN
    )
    assert (
        evaluate_job_health(JobHealthInputs(NOW, None, None, None, (), overdue)).state
        is JobHealthState.ALERT
    )


def test_run_count_mismatch_alert_precedes_unknown() -> None:
    before = datetime(2026, 8, 18, 17, 30, tzinfo=UTC)
    mismatched = JobRunSnapshot(
        1,
        JobName.MISSING_CHECK_OUT,
        before,
        before,
        JobRunStatus.SUCCEEDED,
        1,
        1,
        0,
        None,
    )
    health = evaluate_job_health(
        JobHealthInputs(before, mismatched, mismatched, mismatched, (), EMPTY)
    )
    assert health.state is JobHealthState.ALERT
    assert health.reasons.run_count_mismatch
