from __future__ import annotations

from django.db import connection, transaction

from attendance.ports.job_runs import ReconciliationFinalization
from operations.adapters.persistence.job_runs import DjangoJobRunRepository
from operations.domain.job_runs import JobRunCounterDelta, classify_terminal


class DjangoReconciliationJobRuns:
    def __init__(self, repository: DjangoJobRunRepository | None = None) -> None:
        self._repository = repository or DjangoJobRunRepository()

    def create(self, started_at):  # type: ignore[no-untyped-def]
        return self._repository.create(started_at).id

    def record_scan(self, run_id: int, *, changed: bool) -> None:
        self._repository.add_counts(run_id, JobRunCounterDelta(1, int(changed), int(changed)))

    def record_failed_scan(self, run_id: int) -> None:
        self._repository.add_counts(run_id, JobRunCounterDelta(1, 0, 0))

    def changed_count(self, run_id: int) -> int:
        return self._repository.get(run_id).changed_count

    def counts(self, run_id: int) -> tuple[int, int, int]:
        run = self._repository.get(run_id)
        return run.scanned_count, run.changed_count, run.anomaly_count

    def finalize(self, run_id: int, finalization: ReconciliationFinalization) -> str | None:
        terminal = classify_terminal(
            self.changed_count(run_id),
            session_failed=finalization.session_failed,
            aborted=finalization.aborted,
        )
        result = self._repository.finalize(run_id, finalization.finished_at, terminal)
        return result.status.value if result else None


class DjangoReadOnlyRepeatableRead:
    def __init__(self) -> None:
        self._outer_atomic = connection.in_atomic_block
        self._atomic = transaction.atomic()

    def __enter__(self):  # type: ignore[no-untyped-def]
        value = self._atomic.__enter__()
        if not self._outer_atomic:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return value

    def __exit__(self, exc_type, exc_value, traceback):  # type: ignore[no-untyped-def]
        return self._atomic.__exit__(exc_type, exc_value, traceback)
