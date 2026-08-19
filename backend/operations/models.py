from __future__ import annotations

from typing import ClassVar

from django.db import models

from operations.domain.job_runs import JobName, JobRunErrorCode, JobRunStatus


class JobRun(models.Model):
    job_name: models.CharField[str, str] = models.CharField(max_length=32)
    started_at: models.DateTimeField = models.DateTimeField()
    finished_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    status: models.CharField[str, str] = models.CharField(
        max_length=32,
        default=JobRunStatus.RUNNING.value,
        db_default=JobRunStatus.RUNNING.value,
    )
    scanned_count: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        default=0, db_default=0
    )
    changed_count: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        default=0, db_default=0
    )
    anomaly_count: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        default=0, db_default=0
    )
    error_code: models.CharField[str | None, str | None] = models.CharField(
        max_length=32, null=True, blank=True
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(job_name__in=[item.value for item in JobName]),
                name="job_run_name_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[item.value for item in JobRunStatus]),
                name="job_run_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(error_code__isnull=True)
                | models.Q(error_code__in=[item.value for item in JobRunErrorCode]),
                name="job_run_error_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status=JobRunStatus.RUNNING.value,
                        finished_at__isnull=True,
                        error_code__isnull=True,
                    )
                    | models.Q(
                        status=JobRunStatus.SUCCEEDED.value,
                        finished_at__isnull=False,
                        error_code__isnull=True,
                    )
                    | models.Q(
                        status__in=[
                            JobRunStatus.PARTIAL_FAILED.value,
                            JobRunStatus.FAILED.value,
                        ],
                        finished_at__isnull=False,
                        error_code__isnull=False,
                    )
                ),
                name="job_run_terminal_shape",
            ),
            models.CheckConstraint(
                condition=models.Q(finished_at__isnull=True)
                | models.Q(finished_at__gte=models.F("started_at")),
                name="job_run_finish_order",
            ),
            models.CheckConstraint(
                condition=models.Q(changed_count=models.F("anomaly_count"))
                & models.Q(scanned_count__gte=models.F("changed_count")),
                name="job_run_counts_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=JobRunStatus.RUNNING.value)
                    | models.Q(status=JobRunStatus.SUCCEEDED.value)
                    | models.Q(
                        status=JobRunStatus.PARTIAL_FAILED.value,
                        changed_count__gt=0,
                        error_code=JobRunErrorCode.SESSION_PROCESSING_FAILED.value,
                    )
                    | models.Q(
                        status=JobRunStatus.FAILED.value,
                        changed_count=0,
                        error_code=JobRunErrorCode.SESSION_PROCESSING_FAILED.value,
                    )
                    | models.Q(
                        status=JobRunStatus.FAILED.value,
                        changed_count=0,
                        error_code=JobRunErrorCode.RUN_ABORTED.value,
                    )
                ),
                name="job_run_failure_shape",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["job_name", "started_at", "id"], name="job_run_started_idx"),
            models.Index(
                fields=["job_name", "status", "finished_at", "id"],
                name="job_run_status_idx",
            ),
        ]
