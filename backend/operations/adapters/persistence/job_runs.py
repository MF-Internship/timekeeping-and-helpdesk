from __future__ import annotations

from datetime import datetime

from django.db.models import F

from operations.domain.job_runs import (
    JobName,
    JobRunCounterDelta,
    JobRunErrorCode,
    JobRunSnapshot,
    JobRunStatus,
    JobRunTerminal,
)
from operations.models import JobRun


class DjangoJobRunRepository:
    def create(self, started_at: datetime) -> JobRunSnapshot:
        model = JobRun.objects.create(
            job_name=JobName.MISSING_CHECK_OUT.value,
            started_at=started_at,
        )
        return job_run_snapshot(model)

    def add_counts(self, run_id: int, delta: JobRunCounterDelta) -> JobRunSnapshot:
        scanned, changed, anomaly = delta.scanned, delta.changed, delta.anomaly
        if min(scanned, changed, anomaly) < 0 or changed != anomaly or changed > scanned:
            raise ValueError("job_run_counts")
        updated = JobRun.objects.filter(pk=run_id, status=JobRunStatus.RUNNING.value).update(
            scanned_count=F("scanned_count") + scanned,
            changed_count=F("changed_count") + changed,
            anomaly_count=F("anomaly_count") + anomaly,
        )
        if updated != 1:
            raise RuntimeError("job_run_not_running")
        return self.get(run_id)

    def finalize(
        self, run_id: int, finished_at: datetime, terminal: JobRunTerminal
    ) -> JobRunSnapshot | None:
        updated = JobRun.objects.filter(pk=run_id, status=JobRunStatus.RUNNING.value).update(
            status=terminal.status.value,
            error_code=terminal.error_code.value if terminal.error_code else None,
            finished_at=finished_at,
        )
        return self.get(run_id) if updated == 1 else None

    def get(self, run_id: int, *, lock: bool = False) -> JobRunSnapshot:
        query = JobRun.objects.select_for_update() if lock else JobRun.objects
        return job_run_snapshot(query.get(pk=run_id))

    def latest(self) -> JobRunSnapshot | None:
        return _snapshot_or_none(JobRun.objects.order_by("-started_at", "-id").first())

    def latest_successful(self) -> JobRunSnapshot | None:
        model = (
            JobRun.objects.filter(status=JobRunStatus.SUCCEEDED.value)
            .order_by("-finished_at", "-id")
            .first()
        )
        return _snapshot_or_none(model)

    def latest_terminal(self) -> JobRunSnapshot | None:
        model = (
            JobRun.objects.exclude(status=JobRunStatus.RUNNING.value)
            .order_by("-finished_at", "-id")
            .first()
        )
        return _snapshot_or_none(model)

    def unfinished(self) -> tuple[JobRunSnapshot, ...]:
        query = JobRun.objects.filter(status=JobRunStatus.RUNNING.value).order_by(
            "started_at", "id"
        )
        return tuple(job_run_snapshot(model) for model in query)


def job_run_snapshot(model: JobRun) -> JobRunSnapshot:
    return JobRunSnapshot(
        model.pk,
        JobName(model.job_name),
        model.started_at,
        model.finished_at,
        JobRunStatus(model.status),
        model.scanned_count,
        model.changed_count,
        model.anomaly_count,
        JobRunErrorCode(model.error_code) if model.error_code else None,
    )


def _snapshot_or_none(model: JobRun | None) -> JobRunSnapshot | None:
    return job_run_snapshot(model) if model is not None else None
