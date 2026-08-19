from datetime import UTC, datetime, timedelta

import pytest

from attendance.adapters.persistence.reconciliation import DjangoReconciliationRepository
from operations.adapters.persistence.job_runs import DjangoJobRunRepository
from operations.domain.job_runs import JobRunStatus, JobRunTerminal

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_latest_success_terminal_and_unfinished_queries_are_independent() -> None:
    repository = DjangoJobRunRepository()
    start = datetime(2026, 8, 19, tzinfo=UTC)
    success = repository.create(start)
    repository.finalize(
        success.id, start + timedelta(minutes=1), JobRunTerminal(JobRunStatus.SUCCEEDED, None)
    )
    running = repository.create(start + timedelta(minutes=2))
    assert repository.latest().id == running.id  # type: ignore[union-attr]
    assert repository.latest_successful().id == success.id  # type: ignore[union-attr]
    assert repository.latest_terminal().id == success.id  # type: ignore[union-attr]
    assert [item.id for item in repository.unfinished()] == [running.id]


def test_empty_attendance_evidence_has_zero_aggregates() -> None:
    evidence = DjangoReconciliationRepository().read_evidence(datetime.now(UTC).date())
    assert evidence.overdue_open_session_count == 0
    assert evidence.job_closed_session_count == 0
    assert evidence.missing_checkout_anomaly_count == 0
    assert evidence.job_closed_without_anomaly_count == 0
    assert evidence.anomaly_without_job_closed_count == 0
