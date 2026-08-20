from datetime import UTC, date, datetime

import pytest

from attendance.application.reconciliation import ReconciliationDependencies, ReconciliationService


class Clock:
    def now(self) -> datetime:
        return datetime(2026, 8, 19, tzinfo=UTC)


class UnitOfWork:
    def __enter__(self):  # type: ignore[no-untyped-def]
        return self

    def __exit__(self, *args):  # type: ignore[no-untyped-def]
        return None


class Repository:
    def __init__(self, *, abort: bool = False, fail_id: int | None = None) -> None:
        self.abort = abort
        self.fail_id = fail_id
        self.locked: list[int] = []

    def candidate_ids(self, current_date: date) -> tuple[int, ...]:
        if self.abort:
            raise RuntimeError("scan failed")
        return (1, 2, 3)

    def reconcile_locked(self, session_id: int, current_date: date) -> bool:
        self.locked.append(session_id)
        if session_id == self.fail_id:
            raise RuntimeError("session failed")
        return session_id != 2


class JobRuns:
    def __init__(self, *, finalize: bool = True) -> None:
        self.events: list[object] = []
        self.scanned = 0
        self.changed = 0
        self.finalize_result = finalize

    def create(self, started_at: datetime) -> int:
        self.events.append("created")
        return 7

    def record_scan(self, run_id: int, *, changed: bool) -> None:
        self.events.append(("scan", changed))
        self.scanned += 1
        self.changed += int(changed)

    def record_failed_scan(self, run_id: int) -> None:
        self.events.append("failed-scan")
        self.scanned += 1

    def changed_count(self, run_id: int) -> int:
        return self.changed

    def counts(self, run_id: int) -> tuple[int, int, int]:
        return self.scanned, self.changed, self.changed

    def finalize(self, run_id, finalization):  # type: ignore[no-untyped-def]
        self.events.append(finalization)
        if not self.finalize_result:
            return None
        if finalization.aborted:
            return "FAILED"
        return "PARTIAL_FAILED" if finalization.session_failed else "SUCCEEDED"


def service(repository: Repository, runs: JobRuns) -> ReconciliationService:
    return ReconciliationService(ReconciliationDependencies(Clock(), repository, runs, UnitOfWork))


def test_run_commits_running_before_scan_and_counts_changed_and_noop() -> None:
    repository, runs = Repository(), JobRuns()
    result = service(repository, runs).run()
    assert runs.events[0] == "created"
    assert repository.locked == [1, 2, 3]
    assert (result.status, result.scanned_count, result.changed_count) == ("SUCCEEDED", 3, 2)


def test_run_continues_after_session_failure_and_records_recovery_scan() -> None:
    repository, runs = Repository(fail_id=2), JobRuns()
    result = service(repository, runs).run()
    assert repository.locked == [1, 2, 3]
    assert (result.status, result.scanned_count, result.changed_count) == ("PARTIAL_FAILED", 3, 2)
    assert "failed-scan" in runs.events


def test_scan_abort_is_failed_and_finalization_cas_failure_leaves_running() -> None:
    result = service(Repository(abort=True), JobRuns()).run()
    assert (result.status, result.error_code) == ("FAILED", "RUN_ABORTED")
    with pytest.raises(RuntimeError, match="job_run_finalization_failed"):
        service(Repository(), JobRuns(finalize=False)).run()
