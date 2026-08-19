from datetime import UTC, datetime, timedelta

import pytest
from django.db import IntegrityError, transaction

from operations.adapters.persistence.job_runs import DjangoJobRunRepository
from operations.domain.job_runs import (
    JobRunCounterDelta,
    JobRunErrorCode,
    JobRunStatus,
    JobRunTerminal,
)
from operations.models import JobRun

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]

START = datetime(2026, 8, 19, tzinfo=UTC)


def test_running_is_durable_counts_survive_and_terminal_cas_is_single_use() -> None:
    repository = DjangoJobRunRepository()
    running = repository.create(START)
    assert JobRun.objects.get(pk=running.id).status == "RUNNING"
    counted = repository.add_counts(running.id, JobRunCounterDelta(2, 1, 1))
    assert (counted.status, counted.scanned_count, counted.changed_count) == (
        JobRunStatus.RUNNING,
        2,
        1,
    )
    terminal = JobRunTerminal(JobRunStatus.SUCCEEDED, None)
    assert repository.finalize(running.id, START + timedelta(minutes=1), terminal) is not None
    assert repository.finalize(running.id, START + timedelta(minutes=2), terminal) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"job_name": "OTHER"},
        {"status": "OTHER"},
        {"error_code": "raw exception"},
        {"status": "SUCCEEDED", "finished_at": None},
        {"status": "RUNNING", "finished_at": START},
        {"status": "SUCCEEDED", "finished_at": START - timedelta(seconds=1)},
        {"scanned_count": 0, "changed_count": 1, "anomaly_count": 1},
        {"scanned_count": 1, "changed_count": 1, "anomaly_count": 0},
        {
            "status": "PARTIAL_FAILED",
            "finished_at": START,
            "error_code": JobRunErrorCode.SESSION_PROCESSING_FAILED.value,
            "changed_count": 0,
        },
        {
            "status": "FAILED",
            "finished_at": START,
            "error_code": JobRunErrorCode.RUN_ABORTED.value,
            "scanned_count": 1,
            "changed_count": 1,
            "anomaly_count": 1,
        },
    ],
)
def test_database_rejects_invalid_job_run_shapes(overrides: dict[str, object]) -> None:
    values: dict[str, object] = {
        "job_name": "MISSING_CHECK_OUT",
        "started_at": START,
        "status": "RUNNING",
        "finished_at": None,
        "scanned_count": 0,
        "changed_count": 0,
        "anomaly_count": 0,
        "error_code": None,
    }
    values.update(overrides)
    with pytest.raises(IntegrityError), transaction.atomic():
        JobRun.objects.create(**values)
