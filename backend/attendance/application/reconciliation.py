from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from attendance.domain.reconciliation import ReconciliationOutcome
from attendance.ports.clock import Clock
from attendance.ports.job_runs import ReconciliationFinalization, ReconciliationJobRuns
from attendance.ports.reconciliation import ReconciliationRepository
from attendance.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class ReconciliationDependencies:
    clock: Clock
    repository: ReconciliationRepository
    job_runs: ReconciliationJobRuns
    unit_of_work_factory: Callable[[], UnitOfWork]


class ReconciliationService:
    def __init__(self, dependencies: ReconciliationDependencies) -> None:
        self._dependencies = dependencies

    def run(self) -> ReconciliationOutcome:
        started_at = self._dependencies.clock.now()
        run_id = self._dependencies.job_runs.create(started_at)
        current_date = started_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
        candidate_ids, aborted = self._candidates(current_date)
        failed = self._process(run_id, current_date, candidate_ids) if not aborted else False
        finalization = ReconciliationFinalization(self._dependencies.clock.now(), failed, aborted)
        status = self._dependencies.job_runs.finalize(run_id, finalization)
        if status is None:
            raise RuntimeError("job_run_finalization_failed")
        scanned_count, changed_count, anomaly_count = self._dependencies.job_runs.counts(run_id)
        return ReconciliationOutcome(
            run_id,
            status,
            scanned_count,
            changed_count,
            anomaly_count,
            "RUN_ABORTED" if aborted else ("SESSION_PROCESSING_FAILED" if failed else None),
        )

    def _candidates(self, current_date: date) -> tuple[tuple[int, ...], bool]:
        try:
            return self._dependencies.repository.candidate_ids(current_date), False
        except Exception:
            return (), True

    def _process(self, run_id: int, current_date: date, candidate_ids: tuple[int, ...]) -> bool:
        failed = False
        for session_id in candidate_ids:
            try:
                with self._dependencies.unit_of_work_factory():
                    changed = self._dependencies.repository.reconcile_locked(
                        session_id, current_date
                    )
                    self._dependencies.job_runs.record_scan(run_id, changed=changed)
            except Exception:
                failed = True
                with self._dependencies.unit_of_work_factory():
                    self._dependencies.job_runs.record_failed_scan(run_id)
        return failed
